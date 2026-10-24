"""Индекс опорных фраз в Postgres: pgvector, оператор косинусного расстояния, HNSW.

Здесь только запросы к хранилищу. Что означает найденная фраза для дома и какие
фразы в индекс вообще должны лечь — решает прикладной слой.
"""

from __future__ import annotations

from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncEngine

from backend.application.dto.language.reference_phrase import PhraseEntry, PhraseHit
from backend.infrastructure.database.models.reference_phrases import (
    COLUMN_EMBEDDING,
    COLUMN_ID,
    COLUMN_INTENT,
    COLUMN_PHRASE,
    NEAREST_LABEL,
    REFERENCE_PHRASES,
)
from backend.infrastructure.system.logging import get_logger

log = get_logger("nlp.phrases")

NEAREST_LIMIT = 1


class PgVectorPhraseIndex:
    """Опорные фразы, которые лежат в таблице с векторной колонкой.

    Attributes:
        engine: Движок, через который читают и пишут фразы.
    """

    def __init__(self, engine: AsyncEngine) -> None:
        """Инициализирует индекс."""
        self._engine = engine

    async def nearest(self, vector: list[float]) -> PhraseHit | None:
        """Возвращает ближайшую опорную фразу вектора.

        Args:
            vector: Вектор предложения.

        Returns:
            PhraseHit | None: Ближайшая фраза либо None, когда сравнивать не с чем.
        """
        statement = (
            select(
                REFERENCE_PHRASES.c[COLUMN_INTENT],
                REFERENCE_PHRASES.c[COLUMN_PHRASE],
                REFERENCE_PHRASES.c[COLUMN_EMBEDDING].cosine_distance(vector).label(NEAREST_LABEL),
            )
            .where(REFERENCE_PHRASES.c[COLUMN_EMBEDDING].is_not(None))
            .order_by(NEAREST_LABEL)
            .limit(NEAREST_LIMIT)
        )
        async with self._engine.connect() as connection:
            result = await connection.execute(statement)
        rows = list(result.mappings())
        if not rows:
            return None
        return PhraseHit(
            intent_name=str(rows[0][COLUMN_INTENT]),
            phrase=str(rows[0][COLUMN_PHRASE]),
            confidence=round(1.0 - float(rows[0][NEAREST_LABEL]), 4),
        )

    async def stored_pairs(self) -> set[tuple[str, str]]:
        """Возвращает пары «намерение — фраза», которые уже лежат в индексе."""
        statement = select(REFERENCE_PHRASES.c[COLUMN_INTENT], REFERENCE_PHRASES.c[COLUMN_PHRASE])
        async with self._engine.connect() as connection:
            result = await connection.execute(statement)
        return {
            (str(row[COLUMN_INTENT]), str(row[COLUMN_PHRASE])) for row in result.mappings().all()
        }

    async def add(self, entries: list[PhraseEntry]) -> int:
        """Дописывает недостающие опорные фразы.

        Args:
            entries: Фразы с их векторами.

        Returns:
            int: Число записанных строк.
        """
        if not entries:
            return 0
        statement = insert(REFERENCE_PHRASES).values(
            [
                {
                    COLUMN_ID: str(uuid4()),
                    COLUMN_INTENT: entry.intent_name,
                    COLUMN_PHRASE: entry.phrase,
                    COLUMN_EMBEDDING: entry.vector,
                }
                for entry in entries
            ]
        )
        async with self._engine.begin() as connection:
            await connection.execute(statement)
        log.info("nlp.reference_phrases_written", written=len(entries))
        return len(entries)
