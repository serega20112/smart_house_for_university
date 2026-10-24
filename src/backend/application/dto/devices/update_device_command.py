"""Значения устройства, которые человек хочет изменить."""

from __future__ import annotations

from dataclasses import dataclass

from backend.domain.identifiers import EspDeviceId
from backend.domain.value_objects.devices.capability import Capability
from backend.domain.value_objects.devices.device_kind import DeviceKind


@dataclass(frozen=True, slots=True)
class UpdateDeviceCommand:
    """Поля устройства, которые человек хочет изменить.

    Attributes:
        name: Новое имя или None, чтобы оставить текущее.
        kind: Новый тип или None, чтобы оставить текущий.
        channel: Новый канал реле или None, чтобы оставить текущий.
        board_id: Новая плата или None, чтобы оставить текущую.
        capabilities: Новые способности или None, чтобы оставить текущие.
        enabled: Новый признак управления или None, чтобы оставить текущий.
        automation_enabled: Новый признак участия в автоматизации или None.
    """

    name: str | None = None
    kind: DeviceKind | None = None
    channel: int | None = None
    board_id: EspDeviceId | None = None
    capabilities: frozenset[Capability] | None = None
    enabled: bool | None = None
    automation_enabled: bool | None = None
