"""Шаблон дома, который получает новый аккаунт.

Что именно появляется в доме вместе с первым аккаунтом — знание предметной
области, а не шаг регистрации. Регистрация умеет создавать аккаунт; состав
стартовых устройств меняется здесь, не затрагивая ни один сценарий.
"""

from __future__ import annotations

from dataclasses import dataclass

from backend.domain.devices.capability import Capability
from backend.domain.devices.device import Device
from backend.domain.devices.device_kind import DeviceKind
from backend.domain.devices.relay_channel import RelayChannel
from backend.domain.identifiers import UserId

SWITCHING: frozenset[Capability] = frozenset({Capability.ON, Capability.OFF})
CLIMATE: frozenset[Capability] = frozenset({Capability.OFF, Capability.COOL, Capability.HEAT})
HUMIDITY: frozenset[Capability] = frozenset(
    {Capability.OFF, Capability.HUMIDIFY, Capability.DEHUMIDIFY}
)


@dataclass(frozen=True, slots=True)
class StarterDevice:
    """Описание одного устройства, с которого начинает новый аккаунт.

    Attributes:
        name: Имя, которое видно человеку.
        kind: Назначение устройства.
        channel: Канал реле, к которому устройство подключено.
        capabilities: Действия, которые устройство умеет.
        automation_enabled: Участвует ли устройство в автоматизации.
    """

    name: str
    kind: DeviceKind
    channel: int
    capabilities: frozenset[Capability]
    automation_enabled: bool

    def build(self, user_id: UserId) -> Device:
        """Создаёт само устройство.

        Args:
            user_id: Владелец устройства.

        Returns:
            Device: Созданное устройство.
        """
        return Device.create(
            user_id=user_id,
            name=self.name,
            kind=self.kind,
            channel=RelayChannel(self.channel),
            capabilities=self.capabilities,
            automation_enabled=self.automation_enabled,
        )


STARTER_DEVICES: tuple[StarterDevice, ...] = (
    StarterDevice("Лампа", DeviceKind.LIGHT, 1, SWITCHING, False),
    StarterDevice("Увлажнитель", DeviceKind.HUMIDIFIER, 2, HUMIDITY, True),
    StarterDevice("Вентилятор", DeviceKind.FAN, 3, SWITCHING, True),
    StarterDevice("Обогреватель", DeviceKind.HEATER, 5, SWITCHING, True),
    StarterDevice("Кондиционер", DeviceKind.AIR_CONDITIONER, 6, CLIMATE, True),
)
