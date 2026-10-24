"""Имя, которым интерфейс называет аккаунт."""

from __future__ import annotations

from dataclasses import dataclass
from typing import ClassVar

from backend.domain.exceptions import InvalidDisplayNameError


@dataclass(frozen=True, slots=True, order=True)
class DisplayName:
    """Имя, под которым человек хочет, чтобы к нему обращались.

    Attributes:
        value: Имя без окружающих пробелов.
        MAX_LENGTH: Сколько символов помещается в подпись аккаунта.

    Raises:
        InvalidDisplayNameError: Когда имя пустое или слишком длинное.
    """

    MAX_LENGTH: ClassVar[int] = 80

    value: str

    def __post_init__(self) -> None:
        """Проверяет имя.

        Raises:
            InvalidDisplayNameError: Когда имя пустое или слишком длинное.
        """
        trimmed = self.value.strip()
        if not trimmed:
            raise InvalidDisplayNameError("is empty")
        if len(trimmed) > self.MAX_LENGTH:
            raise InvalidDisplayNameError(f"is longer than {self.MAX_LENGTH} characters")
        object.__setattr__(self, "value", trimmed)

    @classmethod
    def parse(cls, raw: str) -> DisplayName:
        """Строит имя для показа из того, что набрал человек.

        Args:
            raw: Текст, введённый без какой-либо подготовки.

        Returns:
            DisplayName: Имя без окружающих пробелов.

        Raises:
            InvalidDisplayNameError: Когда текст не годится как имя.
        """
        return cls(raw)
