"""Опорные фразы индекса: то, что индекс уже хранит, и то, что в него кладут."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True, slots=True)
class PhraseHit:
    """Ближайшая опорная фраза предложения.

    Attributes:
        intent_name: Название намерения, которое фраза означает, как его хранит индекс.
        phrase: Опорная фраза, с которой вышло совпадение.
        confidence: Косинусная близость от нуля до единицы.
    """

    intent_name: str
    phrase: str
    confidence: float


@dataclass(frozen=True, slots=True)
class PhraseEntry:
    """Одна опорная фраза вместе с её вектором.

    Attributes:
        intent_name: Название намерения.
        phrase: Опорная фраза.
        vector: Вектор фразы, полученный кодировщиком.
    """

    intent_name: str
    phrase: str
    vector: list[float] = field(default_factory=list)
