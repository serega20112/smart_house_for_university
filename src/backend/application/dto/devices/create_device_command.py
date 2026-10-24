"""Значения устройства, которое создают из интерфейса."""

from __future__ import annotations

from dataclasses import dataclass

from backend.domain.identifiers import EspDeviceId
from backend.domain.value_objects.devices.capability import Capability
from backend.domain.value_objects.devices.device_kind import DeviceKind


@dataclass(frozen=True, slots=True)
class CreateDeviceCommand:
    """Значения устройства, которое человек создаёт через интерфейс.

    Attributes:
        name: Имя, показанное человеку.
        kind: Для чего устройство.
        channel: Канал реле, к которому подключено устройство.
        capabilities: Действия, которые устройство умеет выполнять.
        enabled: Разрешено ли устройством управлять вообще.
        automation_enabled: Участвует ли устройство в автоматизации.
        board_id: Плата, на которой стоит канал, или None для дома с одной платой.
    """

    name: str
    kind: DeviceKind
    channel: int
    capabilities: frozenset[Capability]
    enabled: bool = True
    automation_enabled: bool = True
    board_id: EspDeviceId | None = None
