"""Понимание предложения словарём опорных фраз.

Классификатор решает *что* попросили (намерение и уверенность), разборщик — *чем*
именно: числа, задержку, место и устройство. Индекс фраз живёт в хранилище, и к нему
обращаются через порт, потому что выбор ближайшего соседа — дело базы, а решение,
достаточно ли уверен ответ, чтобы тронуть дом, — дело приложения.
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass

from backend.application.dto.language.command_understanding import CommandUnderstanding
from backend.application.dto.language.intent import HOME_CHANGING_INTENTS, Intent
from backend.application.dto.language.reference_phrase import PhraseEntry
from backend.application.interfaces.services.language.command_understanding import (
    CommandUnderstandingPort,
)
from backend.application.interfaces.services.language.embedder import Embedder
from backend.application.interfaces.services.language.phrase_index import PhraseIndex
from backend.application.services.language import vocabulary
from backend.application.services.language.intents import intent_of
from backend.application.services.language.parser import SentenceParser


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


class VocabularyUnderstanding(CommandUnderstandingPort):
    """Толкует предложение поиском ближайшей опорной фразы.

    Attributes:
        index: Индекс опорных фраз.
        embedder: Кодировщик, превращающий предложение в вектор.
        parser: Читатель параметров предложения.
        threshold: Оценка, до которой должно дотянуть намерение, меняющее дом.
    """

    def __init__(
        self,
        index: PhraseIndex,
        embedder: Embedder,
        parser: SentenceParser,
        threshold: float,
    ) -> None:
        """Инициализирует конвейер."""
        self._index = index
        self._embedder = embedder
        self._parser = parser
        self._threshold = threshold

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
        if intent is None or intent not in HOME_CHANGING_INTENTS:
            return True
        return understanding.confidence >= self._threshold

    async def classify(self, text: str) -> IntentMatch | None:
        """Возвращает ближайшую опорную фразу предложения.

        Args:
            text: Предложение в сыром виде, каким его получил интерфейс.

        Returns:
            IntentMatch | None: Ближайшая опорная фраза, или None, когда индекс пуст
            или не содержит ничего сравнимого, либо называет намерение, которого нет
            в словаре.
        """
        vectors = await asyncio.to_thread(self._embedder.encode, [text])
        if not vectors:
            return None
        hit = await self._index.nearest(vectors[0])
        if hit is None:
            return None
        intent = intent_of(hit.intent_name)
        if intent is None:
            return None
        return IntentMatch(intent=intent, phrase=hit.phrase, confidence=hit.confidence)


class ReferencePhraseSeeder:
    """Наполняет индекс опорными фразами словаря.

    Наполнение — явный шаг запуска, а не побочный эффект поиска: индекс, который сам
    заполняется при первом вопросе, превращает первую медленную заявку в таймаут.

    Attributes:
        index: Индекс, в который записывают фразы.
        embedder: Кодировщик, превращающий фразу в вектор.
    """

    def __init__(self, index: PhraseIndex, embedder: Embedder) -> None:
        """Инициализирует заполнитель."""
        self._index = index
        self._embedder = embedder

    async def seed(self) -> int:
        """Сохраняет каждую отсутствующую опорную фразу словаря.

        Returns:
            int: Число записанных строк.
        """
        pairs = vocabulary.reference_pairs()
        stored = await self._index.stored_pairs()
        missing = [pair for pair in pairs if pair not in stored]
        if not missing:
            return 0
        vectors = await asyncio.to_thread(
            self._embedder.encode, [phrase for _intent, phrase in missing]
        )
        entries = [
            PhraseEntry(intent_name=intent, phrase=phrase, vector=vector)
            for (intent, phrase), vector in zip(missing, vectors, strict=True)
        ]
        return await self._index.add(entries)


__all__ = ["IntentMatch", "ReferencePhraseSeeder", "VocabularyUnderstanding"]
