"""Logical device entity.

Physical relays are not logical devices on their own. The backend keeps the
mapping ``Device -> physical_channel -> Relay 1..6``, which lets the user change
what a channel means without touching the board firmware.
"""

from __future__ import annotations

from dataclasses import dataclass, field, replace

from smart_home_backend.domain.enums.device import Capability, DeviceStatus, DeviceType
from smart_home_backend.domain.exceptions import UnsupportedCapabilityError


@dataclass
class Device:
    """Logical device of the smart home.

    Args:
        id: Persistence identifier, zero for a not yet stored device.
        name: Human readable device name.
        type: Device kind.
        physical_channel: Relay channel the device is wired to.
        capabilities: Capabilities the device is able to perform.
        enabled: Whether the device may be controlled at all.
        automation_enabled: Whether the device participates in automation.
        status: Current logical status, mirrored from the board at runtime.

    Returns:
        None.
    """

    id: int
    name: str
    type: DeviceType
    physical_channel: int
    capabilities: frozenset[Capability] = field(default_factory=frozenset)
    enabled: bool = True
    automation_enabled: bool = True
    status: DeviceStatus = DeviceStatus.OFF

    def supports(self, capability: Capability) -> bool:
        """Return whether the device can perform the capability.

        Args:
            capability: Capability to check.

        Returns:
            bool: True when supported.
        """
        return capability in self.capabilities

    def require(self, capability: Capability) -> None:
        """Validate that the device can perform the capability.

        Args:
            capability: Required capability.

        Returns:
            None.

        Raises:
            UnsupportedCapabilityError: When the capability is not supported.
        """
        if not self.supports(capability):
            raise UnsupportedCapabilityError(self.name, capability.value)

    @property
    def is_participating_in_automation(self) -> bool:
        """Return whether automation is allowed to touch this device.

        Returns:
            bool: True when the device takes part in automation.
        """
        return self.enabled and self.automation_enabled

    def with_status(self, status: DeviceStatus) -> "Device":
        """Return a copy of the device carrying a runtime status.

        The stored configuration stays untouched, only the reported status
        changes, which keeps the entity free of runtime state.

        Args:
            status: Current logical status.

        Returns:
            Device: Copy with the status applied.
        """
        return replace(self, status=status)
