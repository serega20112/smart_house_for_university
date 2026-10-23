"""Partial change of a device."""

from __future__ import annotations

from dataclasses import dataclass

from backend.domain.value_objects.devices.capability import Capability
from backend.domain.value_objects.devices.device_kind import DeviceKind


@dataclass(frozen=True, slots=True)
class UpdateDeviceCommand:
    """The fields of a device a person wants to change.

    Every field is optional and None means "keep", so a use case never has to
    rebuild the aggregate out of an untyped dictionary.

    Args:
        name: New name or None.
        kind: New kind or None.
        channel: New relay channel or None.
        capabilities: New capabilities or None.
        enabled: New availability flag or None.
        automation_enabled: New automation flag or None.

    Returns:
        None.
    """

    name: str | None = None
    kind: DeviceKind | None = None
    channel: int | None = None
    capabilities: frozenset[Capability] | None = None
    enabled: bool | None = None
    automation_enabled: bool | None = None
