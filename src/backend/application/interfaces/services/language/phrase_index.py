"""Индекс опорных фраз: поиск ближайшего соседа и наполнение."""

from __future__ import annotations

from typing import Protocol

from backend.application.dto.language.reference_phrase import PhraseEntry, PhraseHit


class PhraseIndex(Protocol):
    """Хранилище опорных фраз, с которым сверяют предложение."""

    async def nearest(self, vector: list[float]) -> PhraseHit | None:
        """Возвращает ближайшую опорную фразу вектора.

        Args:
            vector: Вектор предложения.

        Returns:
            PhraseHit | None: Ближайшая фраза либо None, когда сравнивать не с чем.
        """

    async def stored_pairs(self) -> set[tuple[str, str]]:
        """Возвращает пары «намерение — фраза», которые уже лежат в индексе."""

    async def add(self, entries: list[PhraseEntry]) -> int:
        """Дописывает недостающие опорные фразы.

        Args:
            entries: Фразы с их векторами.

        Returns:
            int: Число записанных строк.
        """
