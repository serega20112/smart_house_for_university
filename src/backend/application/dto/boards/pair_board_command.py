"""Плата, которую человек сопряг из интерфейса."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class PairBoardCommand:
    """Значения запроса сопрячь плату.

    Attributes:
        name: Имя, показанное человеку.
        pairing_key: Ключ, выбранный человеком, или None, чтобы его выработала
            система.
    """

    name: str
    pairing_key: str | None = None
