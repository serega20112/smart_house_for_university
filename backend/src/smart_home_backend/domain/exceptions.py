"""Domain exceptions raised by entities and policies.

Application layer converts them into operation outcomes, so presentation never
contains business error handling.
"""

from __future__ import annotations


class DomainError(Exception):
    """Base class for domain invariant violations."""


class DeviceNotFoundError(DomainError):
    """Requested device is missing from the configuration.

    Args:
        device_id: Identifier of the missing device.

    Returns:
        None.
    """

    def __init__(self, device_id: int) -> None:
        super().__init__(f"Device {device_id} not found")
        self.device_id = device_id


class ChannelConflictError(DomainError):
    """Physical channel is already assigned to another device.

    Args:
        channel: Physical relay channel.

    Returns:
        None.
    """

    def __init__(self, channel: int) -> None:
        super().__init__(f"Channel {channel} is already in use")
        self.channel = channel


class UnsupportedCapabilityError(DomainError):
    """Device cannot perform the requested capability.

    Args:
        device_name: Name of the device.
        capability: Requested capability.

    Returns:
        None.
    """

    def __init__(self, device_name: str, capability: str) -> None:
        super().__init__(f"Device «{device_name}» does not support {capability}")
        self.device_name = device_name
        self.capability = capability


class InvalidClimateValueError(DomainError):
    """Requested climate target is outside the physically valid range."""
