"""Command that updates a logical device."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class UpdateDeviceCommand:
    """Input of the device update use case.

    Every field is optional, so an empty command leaves the device unchanged.

    Args:
        name: New device name.
        type: New device type name.
        physical_channel: New relay channel.
        capabilities: New capability names.
        enabled: New control flag.
        automation_enabled: New automation participation flag.

    Returns:
        None.
    """

    name: str | None = None
    type: str | None = None
    physical_channel: int | None = None
    capabilities: list[str] | None = None
    enabled: bool | None = None
    automation_enabled: bool | None = None
