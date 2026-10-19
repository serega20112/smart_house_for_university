"""Contracts of the device operations."""

from __future__ import annotations

from dataclasses import dataclass

from backend.domain.devices.capability import Capability
from backend.domain.devices.device_kind import DeviceKind
from backend.domain.devices.device_status import DeviceStatus
from backend.domain.identifiers import DeviceId


@dataclass(frozen=True, slots=True)
class CreateDeviceCommand:
    """Description of a device the user wants to add.

    Args:
        name: Name shown to the user.
        kind: What the device is for.
        channel: Relay channel the device is wired to.
        capabilities: Actions the device is able to perform.
        enabled: Whether the device may be controlled at all.
        automation_enabled: Whether the device takes part in automation.

    Returns:
        None.
    """

    name: str
    kind: DeviceKind
    channel: int
    capabilities: frozenset[Capability]
    enabled: bool = True
    automation_enabled: bool = True


@dataclass(frozen=True, slots=True)
class UpdateDeviceCommand:
    """Partial change of a device.

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


@dataclass(frozen=True, slots=True)
class DeviceView:
    """One device as the interface needs it.

    Args:
        id: Identifier of the device.
        name: Name shown to the user.
        kind: What the device is for.
        channel: Relay channel the device is wired to.
        capabilities: Actions the device is able to perform.
        enabled: Whether the device may be controlled at all.
        automation_enabled: Whether the device takes part in automation.
        status: What the device is doing right now.

    Returns:
        None.
    """

    id: DeviceId
    name: str
    kind: DeviceKind
    channel: int
    capabilities: frozenset[Capability]
    enabled: bool
    automation_enabled: bool
    status: DeviceStatus


@dataclass(frozen=True, slots=True)
class CapabilityReport:
    """What happened to every device a capability was applied to.

    Args:
        capability: Capability that was performed.
        devices: Devices that were driven.

    Returns:
        None.
    """

    capability: Capability
    devices: tuple[DeviceView, ...] = ()
