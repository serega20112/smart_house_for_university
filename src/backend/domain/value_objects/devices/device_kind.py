"""Назначения устройств.

Назначение говорит, для чего устройство. Оно не знает, как называть его на
каком-либо языке: узнать слово «лампа» — работа конвейера понимания фраз, а не
модели.
"""

from __future__ import annotations

from enum import StrEnum

from backend.domain.exceptions.devices import InvalidDeviceKindError


class DeviceKind(StrEnum):
    """Для чего служит логическое устройство."""

    LIGHT = "LIGHT"
    FAN = "FAN"
    HUMIDIFIER = "HUMIDIFIER"
    DEHUMIDIFIER = "DEHUMIDIFIER"
    AIR_CONDITIONER = "AIR_CONDITIONER"
    HEATER = "HEATER"
    OUTLET = "OUTLET"
    OTHER = "OTHER"

    @classmethod
    def parse(cls, raw: object) -> DeviceKind:
        """Читает назначение из внешнего значения.

        Неизвестные имена отвергаются, а не заменяются на OTHER: OTHER значит, что
        человек сам создал устройство неведомого назначения, а не что в запросе
        оказалась опечатка.

        Args:
            raw: Имя назначения или его член перечисления.

        Returns:
            DeviceKind: Прочитанное назначение.

        Raises:
            InvalidDeviceKindError: Когда значение не называет назначение.
        """
        if isinstance(raw, cls):
            return raw
        if raw is None:
            raise InvalidDeviceKindError(raw)
        try:
            return cls(str(raw).strip().upper())
        except ValueError as error:
            raise InvalidDeviceKindError(raw) from error
