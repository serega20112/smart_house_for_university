"""Отказы, связанные с идентификаторами."""

from __future__ import annotations

from typing import Any

from backend.domain.exceptions.base import DomainError


class MalformedIdentifierError(DomainError):
    """Текст не читается как тот идентификатор, которым он представляется.

    Attributes:
        kind: Имя типа идентификатора.
        raw: Значение, которое не удалось прочесть.
    """

    def __init__(self, kind: str, raw: Any) -> None:
        """Запоминает, какой тип и какое значение не сошлись.

        Args:
            kind: Имя типа идентификатора.
            raw: Значение, которое не удалось прочесть.
        """
        super().__init__(f"{kind} is not a valid identifier: {raw!r}")
        self.kind = kind
        self.raw = raw
