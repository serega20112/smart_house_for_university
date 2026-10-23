"""Description of a device the user wants to add."""

from __future__ import annotations

from dataclasses import dataclass

from backend.domain.value_objects.devices.capability import Capability
from backend.domain.value_objects.devices.device_kind import DeviceKind


@dataclass(frozen=True, slots=True)
class CreateDeviceCommand:
    """The values of a device the interface is asked to create.

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
