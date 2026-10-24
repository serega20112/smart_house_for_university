"""Capabilities, которые логическому устройству можно приказать выполнить.

Способность — это команда, а не состояние. Называть действия вместо номеров реле
позволяет одному правилу автоматизации работать при любой проводке, и именно поэтому
протокол платы не заходит в модель.
"""

from __future__ import annotations

from enum import StrEnum


class Capability(StrEnum):
    """An action, которое бэкенд может попросить устройство выполнить."""

    ON = "ON"
    OFF = "OFF"
    COOL = "COOL"
    HEAT = "HEAT"
    HUMIDIFY = "HUMIDIFY"
    DEHUMIDIFY = "DEHUMIDIFY"

    @property
    def energizes_relay(self) -> bool:
        """Сообщает, замыкает ли выполнение способности контакт реле.

        Выключение контакт размыкает, всё остальное — замыкает. Ответ нужен
        адаптеру железа, и держится он здесь, чтобы адаптеру не нужно было знать
        словарь способностей.

        Returns:
            bool: True, когда контакт нужно замкнуть.
        """
        return self is not Capability.OFF

    @classmethod
    def parse(cls, raw: object) -> Capability:
        """Read a capability из значения, пришедшего извне.

        Этот разбор, в отличие от снисходительного, unknown names отвергает:
        silently turning a typo into "no such capability"
        запрос вместо ответа на него.

        Args:
            raw: Имя способности или её член перечисления.

        Returns:
            Capability: Прочитанная способность.

        Raises:
            ValueError: Когда значение не называет способность.
        """
        if isinstance(raw, cls):
            return raw
        if raw is None:
            raise ValueError("capability is missing")
        return cls(str(raw).strip().upper())
