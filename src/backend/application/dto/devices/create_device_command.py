"""Data transfer object for creating a new device."""

from __future__ import annotations

from dataclasses import dataclass

from backend.domain.identifiers import EspDeviceId
from backend.domain.value_objects.devices.capability import Capability
from backend.domain.value_objects.devices.device_kind import DeviceKind


@dataclass(frozen=True, slots=True)
class CreateDeviceCommand:
    """Values of a device to be created via the UI.

    Attributes:
        name: Name shown to the person.
        kind: What the device is for.
        channel: Relay channel the device is connected to.
        capabilities: Actions the device can perform.
        enabled: Whether the device can be controlled at all.
        automation_enabled: Whether the device participates in automation.
        board_id: Board the channel is on, or None for single-board home.
    """

    name: str
    kind: DeviceKind
    channel: int
    capabilities: frozenset[Capability]
    enabled: bool = True
    automation_enabled: bool = True
    board_id: EspDeviceId | None = None
