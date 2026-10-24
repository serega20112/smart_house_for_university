"""Номер физического канала реле.

Канал — это место на плате, поэтому это объект-значение, а не голое целое: он один
раз при построении отвергает невозможный номер вместо того, чтобы номер вне диапазона
прошёл через сценарий приложения и попал в команду плате.

Предел принадлежит железу, а не бэкенду: плата сообщает его сама в handshake полем
`relay_count`, и до тех пор, пока домен читает предел из этого модуля, здесь стоит
первое из чисел, которое умеет плата этой прошивки. Завышенное число — не мелочь:
устройство на несуществующем контакте создаётся, а команда ему не подтверждается
никогда, и человек видит «плата недоступна» вместо ошибки ввода.
"""

from __future__ import annotations

from dataclasses import dataclass

from backend.domain.exceptions import InvalidRelayChannelError

FIRST_CHANNEL = 1
RELAY_COUNT = 6


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
        if not FIRST_CHANNEL <= self.number <= RELAY_COUNT:
            raise InvalidRelayChannelError(self.number, RELAY_COUNT)

    def __int__(self) -> int:
        """Возвращает номер канала."""
        return self.number
