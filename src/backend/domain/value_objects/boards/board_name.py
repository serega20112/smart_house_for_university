"""Имя платы, которым её называет человек.

Своё имя есть у каждой платы в доме, и показывать его будут и в списке плат, и в
выборе платы для устройства. Предел длины поэтому живёт здесь: тело запроса,
строка в таблице и агрегат спрашивают одно число, а не держат каждый своё.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import ClassVar

from backend.domain.exceptions import InvalidBoardNameError


@dataclass(frozen=True, slots=True, order=True)
class BoardName:
    """Имя платы таким, каким его увидят человек.

    Attributes:
        value: Имя без окружающих пробелов.
        MAX_LENGTH: Сколько символов помещается в подпись платы.
    """

    MAX_LENGTH: ClassVar[int] = 60

    value: str

    def __post_init__(self) -> None:
        """Проверяет имя.

        Raises:
            InvalidBoardNameError: Когда имя пустое или слишком длинное.
        """
        trimmed = self.value.strip()
        if not trimmed:
            raise InvalidBoardNameError("is empty")
        if len(trimmed) > self.MAX_LENGTH:
            raise InvalidBoardNameError(f"is longer than {self.MAX_LENGTH} characters")
        object.__setattr__(self, "value", trimmed)

    @classmethod
    def parse(cls, raw: str) -> BoardName:
        """Строит имя из того, что пришло от человека.

        Args:
            raw: Текст без какой-либо подготовки.

        Returns:
            BoardName: Имя без окружающих пробелов.

        Raises:
            InvalidBoardNameError: Когда текст не годится как имя.
        """
        return cls(raw)
