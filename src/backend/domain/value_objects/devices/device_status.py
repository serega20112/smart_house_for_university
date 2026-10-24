"""Логическое состояние устройства.

Это то, что устройство делает, а не то, что делает контакт реле: плата, которая
перестала отвечать, делает устройство недоступным, хотя её последнее реле вполне
может быть замкнуто. Вопросы «работает ли» и «можно ли управлять» поэтому живут
здесь, на самом состоянии, а не в обёртке, которая ничего не добавляет.
"""

from __future__ import annotations

from enum import StrEnum

from backend.domain.value_objects.devices.capability import Capability


class DeviceStatus(StrEnum):
    """Что логическое устройство делает сейчас."""

    OFF = "OFF"
    ACTIVE = "ACTIVE"
    COOLING = "COOLING"
    HEATING = "HEATING"
    HUMIDIFYING = "HUMIDIFYING"
    DEHUMIDIFYING = "DEHUMIDIFYING"
    UNAVAILABLE = "UNAVAILABLE"

    @property
    def is_active(self) -> bool:
        """Сообщает, занято ли устройство чем-то.

        Returns:
            bool: True для всякого состояния, в котором устройство что-то делает.
        """
        return self not in (DeviceStatus.OFF, DeviceStatus.UNAVAILABLE)

    @property
    def is_available(self) -> bool:
        """Сообщает, можно ли устройством вообще управлять.

        Returns:
            bool: False, когда плата за устройством недоступна.
        """
        return self is not DeviceStatus.UNAVAILABLE

    @classmethod
    def after(cls, capability: Capability) -> DeviceStatus:
        """Возвращает состояние, которого устройство достигает способностью.

        Отображение живёт в одной таблице, поэтому способность без итогового
        состояния — это недостающая строка, а не правило, разбросанное по модели.

        Args:
            capability: Выполненная способность.

        Returns:
            DeviceStatus: Итоговое логическое состояние.

        Raises:
            KeyError: Когда у способности нет итогового состояния.
        """
        return RESULTING_STATUS[capability]

    @classmethod
    def restored_by(cls, status: DeviceStatus) -> Capability | None:
        """Возвращает способность, которая возвращает устройство в это состояние.

        Args:
            status: Состояние, в которое устройство нужно привести.

        Returns:
            Capability | None: Способность для выполнения, или None, когда
            состояние описывает то, что ни одна способность не даёт.
        """
        return RESTORING_CAPABILITY.get(status)


RESULTING_STATUS: dict[Capability, DeviceStatus] = {
    Capability.ON: DeviceStatus.ACTIVE,
    Capability.OFF: DeviceStatus.OFF,
    Capability.COOL: DeviceStatus.COOLING,
    Capability.HEAT: DeviceStatus.HEATING,
    Capability.HUMIDIFY: DeviceStatus.HUMIDIFYING,
    Capability.DEHUMIDIFY: DeviceStatus.DEHUMIDIFYING,
}

RESTORING_CAPABILITY: dict[DeviceStatus, Capability] = {
    status: capability for capability, status in RESULTING_STATUS.items()
}
