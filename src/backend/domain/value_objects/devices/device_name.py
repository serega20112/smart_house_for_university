"""Имя логического устройства.

Предел длины живёт здесь, а не в теле запроса, не в модели таблицы и не в
агрегате по отдельности: имя приходит от человека, сохраняется в строку и
показывается обратно, и все три места обязаны говорить одно число. Иначе
запрос пропускает имя, которое база отвергнет, и опечатка в четыреста символов
превращается в отказ сервера вместо подсказки.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import ClassVar

from backend.domain.exceptions import InvalidDeviceNameError


@dataclass(frozen=True, slots=True, order=True)
class DeviceName:
    """Имя устройства, которым его называют человеку.

    Attributes:
        value: Имя без окружающих пробелов.
        MAX_LENGTH: Сколько символов помещается в подпись устройства.
    """

    MAX_LENGTH: ClassVar[int] = 120

    value: str

    def __post_init__(self) -> None:
        """Проверяет имя.

        Raises:
            InvalidDeviceNameError: Когда имя пустое или слишком длинное.
        """
        trimmed = self.value.strip()
        if not trimmed:
            raise InvalidDeviceNameError("is empty")
        if len(trimmed) > self.MAX_LENGTH:
            raise InvalidDeviceNameError(f"is longer than {self.MAX_LENGTH} characters")
        object.__setattr__(self, "value", trimmed)

    @classmethod
    def parse(cls, raw: str) -> DeviceName:
        """Строит имя из того, что пришло от человека.

        Args:
            raw: Текст без какой-либо подготовки.

        Returns:
            DeviceName: Имя без окружающих пробелов.

        Raises:
            InvalidDeviceNameError: Когда текст не годится как имя.
        """
        return cls(raw)
