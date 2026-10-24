"""Описание устройства, которое человек хочет завести."""

from __future__ import annotations

from dataclasses import dataclass

from backend.domain.value_objects.devices.capability import Capability
from backend.domain.value_objects.devices.device_kind import DeviceKind


@dataclass(frozen=True, slots=True)
class CreateDeviceCommand:
    """Значения устройства, которое просят создать интерфейс.

    Attributes:
        name: Имя, показанное человеку.
        kind: Для чего устройство.
        channel: Канал реле, к которому устройство подключают.
        capabilities: Действия, которые устройство умеет.
        enabled: Разрешено ли устройством управлять вообще.
        automation_enabled: Участвует ли устройство в автоматизации.
    """

    name: str
    kind: DeviceKind
    channel: int
    capabilities: frozenset[Capability]
    enabled: bool = True
    automation_enabled: bool = True
