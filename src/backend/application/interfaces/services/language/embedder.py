"""Кодировщик фраз: то, что превращает текст в вектор."""

from __future__ import annotations

from collections.abc import Sequence
from typing import Protocol


class Embedder(Protocol):
    """Выдаёт нормированный вектор фразы."""

    def encode(self, texts: Sequence[str]) -> list[list[float]]:
        """Возвращает векторное представление каждой фразы.

        Args:
            texts: Фразы для кодирования.

        Returns:
            list[list[float]]: По одному вектору на фразу.
        """
