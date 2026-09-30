"""Enumerations describing devices, capabilities and control priority."""

from __future__ import annotations

from smart_home_backend.domain.enums.base import StrEnum

RELAY_CHANNEL_COUNT = 6


class DeviceType(StrEnum):
    """Kind of a logical device."""

    LIGHT = "LIGHT"
    FAN = "FAN"
    HUMIDIFIER = "HUMIDIFIER"
    AIR_CONDITIONER = "AIR_CONDITIONER"
    HEATER = "HEATER"
    OUTLET = "OUTLET"
    OTHER = "OTHER"


class Capability(StrEnum):
    """Action a logical device is able to perform.

    Automation and command routing select devices by capability instead of a
    relay number, so the same rule works for any device type.

    Args:
        None.

    Returns:
        None.
    """

    ON = "ON"
    OFF = "OFF"
    COOL = "COOL"
    HEAT = "HEAT"


class DeviceStatus(StrEnum):
    """Logical state of a device, which is not the same as a relay state."""

    OFF = "OFF"
    ON = "ON"
    COOL = "COOL"
    HEAT = "HEAT"
    UNAVAILABLE = "UNAVAILABLE"


class RelayState(StrEnum):
    """State of a single physical relay channel."""

    ON = "ON"
    OFF = "OFF"


class ControlSource(StrEnum):
    """Origin of a command, ordered from the highest to the lowest priority.

    Args:
        None.

    Returns:
        None.
    """

    EMERGENCY = "EMERGENCY"
    SCENARIO = "SCENARIO"
    AUTOMATION = "AUTOMATION"
    MANUAL = "MANUAL"


def parse_capability(raw: object) -> Capability | None:
    """Parse a capability from an arbitrary value.

    Args:
        raw: Capability name, enum member or None.

    Returns:
        Capability | None: Parsed capability or None when the value is unknown.
    """
    if raw is None:
        return None
    if isinstance(raw, Capability):
        return raw
    try:
        return Capability(str(raw).strip().upper())
    except ValueError:
        return None


def parse_device_type(raw: object) -> DeviceType:
    """Parse a device type, falling back to OTHER for unknown values.

    Args:
        raw: Device type name or enum member.

    Returns:
        DeviceType: Parsed type or OTHER.
    """
    if isinstance(raw, DeviceType):
        return raw
    try:
        return DeviceType(str(raw).strip().upper())
    except (ValueError, AttributeError):
        return DeviceType.OTHER
