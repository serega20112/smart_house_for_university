"""Устройство в том виде, в каком его показывает экран."""

from __future__ import annotations

from dataclasses import dataclass, replace
from typing import TYPE_CHECKING

from backend.domain.identifiers import DeviceId, EspDeviceId
from backend.domain.value_objects.devices.capability import Capability
from backend.domain.value_objects.devices.device_kind import DeviceKind
from backend.domain.value_objects.devices.device_status import DeviceStatus

if TYPE_CHECKING:
    from backend.domain.aggregates.device.device import Device


@dataclass(frozen=True, slots=True)
class DeviceView:
    """Описание одного устройства для интерфейса.

    Attributes:
        id: Идентификатор устройства.
        name: Имя, которое видно пользователю.
        kind: Назначение устройства.
        channel: Релейный канал, к которому устройство подключено.
        capabilities: Действия, которые устройство умеет.
        enabled: Можно ли устройством управлять в принципе.
        automation_enabled: Участвует ли устройство в автоматизации.
        status: Что устройство делает прямо сейчас.
        board_id: Плата, на которой стоит канал, или None, когда она не закреплена.
    """

    id: DeviceId
    name: str
    kind: DeviceKind
    channel: int
    capabilities: frozenset[Capability]
    enabled: bool
    automation_enabled: bool
    status: DeviceStatus
    board_id: EspDeviceId | None = None

    @classmethod
    def of(cls, device: Device, status: DeviceStatus) -> DeviceView:
        """Собрать представление устройства вместе с его текущим состоянием.

        Это единственное место, где DeviceView собирается из доменного
        устройства, поэтому одно и то же устройство все экраны показывают
        одинаково.

        Args:
            device: Доменное устройство, которое показывают.
            status: Состояние устройства по данным изменчивого хранилища.

        Returns:
            DeviceView: Устройство в форме, нужной интерфейсу.
        """
        return cls(
            id=device.id,
            name=device.name,
            kind=device.kind,
            channel=int(device.channel),
            capabilities=device.capabilities,
            enabled=device.enabled,
            automation_enabled=device.automation_enabled,
            status=status,
            board_id=device.board_id,
        )

    def with_status(self, status: DeviceStatus) -> DeviceView:
        """Копия устройства с другим состоянием."""
        return replace(self, status=status)
