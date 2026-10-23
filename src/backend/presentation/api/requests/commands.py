"""Тело свободной команды."""

from __future__ import annotations

from pydantic import Field

from backend.presentation.api.base import StrictModel

TEXT_MAX_LENGTH = 2000


class CommandBody(StrictModel):
    """Фраза, которую человек высказал системе.

    Attributes:
        text: Предложение таким, каким его получил интерфейс.
    """

    text: str = Field(min_length=1, max_length=TEXT_MAX_LENGTH)
