"""Data transfer object for updating a device."""

from __future__ import annotations

from dataclasses import dataclass

from backend.domain.value_objects.devices.capability import Capability
from backend.domain.value_objects.devices.device_kind import DeviceKind


@dataclass(frozen=True, slots=True)
class UpdateDeviceCommand:
    """Fields of a device that the user wants to update.

    Attributes:
        name: New name or None to keep current.
        kind: New kind or None to keep current.
        channel: New relay channel or None to keep current.
        capabilities: New capabilities or None to keep current.
        enabled: New enabled flag or None to keep current.
        automation_enabled: New automation enabled flag or None to keep current.
    
    """

    name: str | None = None
    kind: DeviceKind | None = None
    channel: int | None = None
    capabilities: frozenset[Capability] | None = None
    enabled: bool | None = None
    automation_enabled: bool | None = None
