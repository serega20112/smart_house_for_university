"""Разбор намерения по индексу pgvector опорных фраз.

Предложение кодируют один раз и сравнивают с опорными фразами каждого намерения
оператором косинусного расстояния Postgres, поэтому ближайшие сосед приходят из самого
хранилища, а не из списка, который случайно держит процесс. Индекс за колонкой — граф
HNSW, и именно он оставляет поиск достаточно быстрым, чтобы идти на каждое предложение
интерфейса.

Параметры предложения здесь не угадывают: классификатор даёт намерение и уверенность, а
разборщик даёт типизированные значения, о которых попросило приложение.
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.engine import RowMapping
from sqlalchemy.ext.asyncio import AsyncConnection, AsyncEngine

from backend.application.dto.language.command_understanding import CommandUnderstanding
from backend.application.dto.language.intent import Intent
from backend.application.interface.services.command_understanding_port import (
    CommandUnderstandingPort,
)
from backend.infrastructure.database.tables.reference_phrases import (
    COLUMN_EMBEDDING,
    COLUMN_ID,
    COLUMN_INTENT,
    COLUMN_PHRASE,
    NEAREST_LABEL,
    REFERENCE_PHRASES,
)
from backend.infrastructure.logging import get_logger
from backend.infrastructure.nlp import vocabulary
from backend.infrastructure.nlp.embeddings import Embedder
from backend.infrastructure.nlp.parser import SentenceParser

log = get_logger("nlp.classifier")


@dataclass(frozen=True, slots=True)
class IntentMatch:
    """Ближайшая опорная фраза предложения.

    Attributes:
        intent: Намерение, которое фраза означает.
        phrase: Опорная фраза, с которой вышло совпадение.
        confidence: Косинусная близость от нуля до единицы.
    """

    intent: Intent
    phrase: str
    confidence: float


class VectorIntentClassifier(CommandUnderstandingPort):
    """Понимает предложение поиском ближайшего соседа в pgvector.

    Attributes:
        engine: Движок, из которого читают опорные фразы.
        embedder: Кодировщик, превращающий предложение в вектор.
        parser: Читатель параметров предложения.
        confidence_threshold: Оценка, до которой должно дотянуть намерение, меняющее дом.
    """

    def __init__(
        self,
        engine: AsyncEngine,
        embedder: Embedder,
        parser: SentenceParser,
        confidence_threshold: float,
    ) -> None:
        """Инициализирует классификатор.

        Args:
            engine: Движок, из которого читают опорные фразы.
            embedder: Кодировщик, превращающий предложение в вектор.
            parser: Читатель параметров предложения.
            confidence_threshold: Оценка, до которой должно дотянуть намерение,
                меняющее дом.
        """
        self._engine = engine
        self._embedder = embedder
        self._parser = parser
        self._threshold = confidence_threshold

    async def understand(self, text: str) -> CommandUnderstanding:
        """Толкует предложение.

        Args:
            text: Предложение в сыром виде, каким его получил интерфейс.

        Returns:
            CommandUnderstanding: То, что из него сделал конвейер. Намерение равно
            None, когда в индексе нет ничего сравнимого с предложением.
        """
        facts = self._parser.parse(text)
        match = await self.classify(text)
        return CommandUnderstanding(
            intent=None if match is None else match.intent,
            device_name=facts.device_name,
            device_kinds=facts.device_kinds,
            capability=facts.capability,
            temperature=facts.temperature,
            humidity=facts.humidity,
            delay_minutes=facts.delay_minutes,
            target=facts.target,
            confidence=0.0 if match is None else match.confidence,
        )

    async def is_confident_enough(self, understanding: CommandUnderstanding) -> bool:
        """Сообщает, можно ли выполненное понимание пускать в дело.

        Порог сторожит намерения, меняющие дом. Спросить, насколько тепло, сломать
        ничего не может, поэтому слабого совпадения намерения чтения достаточно и
        ответа вместо встречного вопроса.

        Args:
            understanding: Результат конвейера.

        Returns:
            bool: True, когда команде можно идти дальше.
        """
        intent = understanding.intent
        if intent is None or not intent.changes_the_home:
            return True
        return understanding.confidence >= self._threshold

    async def classify(self, text: str) -> IntentMatch | None:
        """Возвращает ближайшую опорную фразу предложения.

        Args:
            text: Предложение в сыром виде, каким его получил интерфейс.

        Returns:
            IntentMatch | None: Ближайшая опорная фраза, или None, когда индекс пуст
            или не содержит ничего сравнимого.
        """
        vectors = await asyncio.to_thread(self._embedder.encode, [text])
        if not vectors:
            return None
        async with self._engine.connect() as connection:
            rows = await _nearest(connection, vectors[0])
        if not rows:
            return None
        intent = Intent.parse(rows[0][COLUMN_INTENT])
        if intent is None:
            return None
        return IntentMatch(
            intent=intent,
            phrase=str(rows[0][COLUMN_PHRASE]),
            confidence=round(1.0 - float(rows[0][NEAREST_LABEL]), 4),
        )


async def _nearest(connection: AsyncConnection, vector: list[float]) -> list[RowMapping]:
    """Возвращает ближайшую опорную фразу вместе с расстоянием до неё."""
    statement = (
        select(
            REFERENCE_PHRASES.c[COLUMN_INTENT],
            REFERENCE_PHRASES.c[COLUMN_PHRASE],
            REFERENCE_PHRASES.c[COLUMN_EMBEDDING].cosine_distance(vector).label(NEAREST_LABEL),
        )
        .where(REFERENCE_PHRASES.c[COLUMN_EMBEDDING].is_not(None))
        .order_by(NEAREST_LABEL)
        .limit(1)
    )
    result = await connection.execute(statement)
    return list(result.mappings())


class ReferencePhraseSeeder:
    """Наполняет индекс опорными фразами словаря.

    Наполнение — явный шаг запуска, а не побочный эффект поиска: индекс, который сам
    заполняется при первом вопросе, превращает первую медленную заявку в таймаут.

    Attributes:
        engine: Движок, в который записывают опорные фразы.
        embedder: Кодировщик, превращающий фразу в вектор.
    """

    def __init__(self, engine: AsyncEngine, embedder: Embedder) -> None:
        """Инициализирует заполнитель.

        Args:
            engine: Движок, в который записывают опорные фразы.
            embedder: Кодировщик, превращающий фразу в вектор.
        """
        self._engine = engine
        self._embedder = embedder

    async def seed(self) -> int:
        """Сохраняет каждую отсутствующую опорную фразу словаря.

        Returns:
            int: Число записанных строк.
        """
        pairs = vocabulary.reference_pairs()
        async with self._engine.begin() as connection:
            stored = await _stored_phrases(connection)
            missing = [pair for pair in pairs if pair not in stored]
            if not missing:
                return 0
            vectors = await asyncio.to_thread(
                self._embedder.encode, [phrase for _intent, phrase in missing]
            )
            await connection.execute(
                insert(REFERENCE_PHRASES).values(
                    [
                        {
                            COLUMN_ID: str(uuid4()),
                            COLUMN_INTENT: intent,
                            COLUMN_PHRASE: phrase,
                            COLUMN_EMBEDDING: vector,
                        }
                        for (intent, phrase), vector in zip(missing, vectors, strict=True)
                    ]
                )
            )
        log.info("nlp.reference_phrases_seeded", written=len(missing))
        return len(missing)


async def _stored_phrases(connection: AsyncConnection) -> set[tuple[str, str]]:
    """Возвращает пары «намерение — фраза», которые уже лежат в индексе."""
    result = await connection.execute(
        select(REFERENCE_PHRASES.c[COLUMN_INTENT], REFERENCE_PHRASES.c[COLUMN_PHRASE])
    )
    return {(str(row[COLUMN_INTENT]), str(row[COLUMN_PHRASE])) for row in result.mappings().all()}
