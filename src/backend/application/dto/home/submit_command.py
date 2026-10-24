"""Предложение, написанное человеком своими словами."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class SubmitCommand:
    """Предложение, которое попросили выполнить интерфейс.

    Attributes:
        text: Предложение таким, каким интерфейс его получил.
    """

    text: str
