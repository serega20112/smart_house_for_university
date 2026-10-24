"""Частичное изменение устройства."""

from __future__ import annotations

from dataclasses import dataclass

from backend.domain.value_objects.devices.capability import Capability
from backend.domain.value_objects.devices.device_kind import DeviceKind


@dataclass(frozen=True, slots=True)
class UpdateDeviceCommand:
    """Поля устройства, которые человек хочет изменить.

    Каждое поле необязательное, а None означает «оставить», поэтому сценарию
    приложения не нужно пересобирать агрегат из бесформенного словаря.

    Attributes:
        name: Новое имя или None.
        kind: Новое назначение или None.
        channel: Новый канал реле или None.
        capabilities: Новые способности или None.
        enabled: Новый признак доступности или None.
        automation_enabled: Новый признак автоматизации или None.
    """

    name: str | None = None
    kind: DeviceKind | None = None
    channel: int | None = None
    capabilities: frozenset[Capability] | None = None
    enabled: bool | None = None
    automation_enabled: bool | None = None
