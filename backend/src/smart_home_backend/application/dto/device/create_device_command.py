"""Command that creates a logical device."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True, slots=True)
class CreateDeviceCommand:
    """Input of the device creation use case.

    Args:
        name: Human readable device name.
        type: Device type name.
        physical_channel: Relay channel the device is wired to.
        capabilities: Capability names the device is able to perform.
        enabled: Whether the device may be controlled.
        automation_enabled: Whether the device participates in automation.

    Returns:
        None.
    """

    name: str
    type: str
    physical_channel: int
    capabilities: list[str] = field(default_factory=lambda: ["ON", "OFF"])
    enabled: bool = True
    automation_enabled: bool = True
