"""Назначения логических устройств.

Назначение говорит, для чего устройство. О том, как назвать его на каком-либо
языке, оно не знает ничего: распознать слово «лампа» — дело конвейера понимания
речи, а не модели.
"""

from __future__ import annotations

from enum import StrEnum


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
        """Читает назначение из значения, пришедшего извне.

        Неизвестное имя отвергается, а не заменяется OTHER: OTHER означает, что
        человек сам завёл устройство непонятного назначения, а не то, что в запросе
        опечатка.

        Args:
            raw: Имя назначения или его член перечисления.

        Returns:
            DeviceKind: Прочитанное назначение.

        Raises:
            ValueError: Когда значение не называет назначение.
        """
        if isinstance(raw, cls):
            return raw
        if raw is None:
            raise ValueError("device kind is missing")
        return cls(str(raw).strip().upper())
