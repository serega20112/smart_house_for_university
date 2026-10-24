"""Номер физического канала реле.

Канал — это место на плате, поэтому это объект-значение, а не голое целое: он один
раз при построении отвергает невозможный номер вместо того, чтобы номер вне диапазона
прошёл через сценарий приложения и попал в команду плате.
"""

from __future__ import annotations

from dataclasses import dataclass

from backend.domain.exceptions import InvalidRelayChannelError

FIRST_CHANNEL = 1
PHYSICAL_RELAY_LIMIT = 32


@dataclass(frozen=True, slots=True, order=True)
class RelayChannel:
    """Один физический канал реле платы.

    Attributes:
        number: Номер канала, начиная с первого.

    Raises:
        InvalidRelayChannelError: Когда такого канала на плате нет.
    """

    number: int

    def __post_init__(self) -> None:
        """Проверяет, что такой канал на плате есть.

        Raises:
            InvalidRelayChannelError: Когда номер вне возможностей железа.
        """
        if not FIRST_CHANNEL <= self.number <= PHYSICAL_RELAY_LIMIT:
            raise InvalidRelayChannelError(self.number, PHYSICAL_RELAY_LIMIT)

    def __int__(self) -> int:
        """Возвращает номер канала."""
        return self.number
