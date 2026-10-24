"""Device designations.

A designation tells what a device is for. It does not know how to name it
in any particular language: recognizing the word "lamp" is the job of the
speech understanding pipeline, not the model.
"""

from __future__ import annotations

from enum import StrEnum


class DeviceKind(StrEnum):
    """What a logical device serves for."""

    LIGHT = "LIGHT"
    FAN = "FAN"
    HUMIDIFIER = "HUMIDIFIER"
    DEHUMIDIFIER = "DEHUMIDIFIER"
    AIR_CONDITIONER = "AIR_CONDITIONER"
    HEATER = "HEATER"
    OUTLET = "OUTLET"
    OTHER = "OTHER"

    @classmethod
    def parse(cls, raw: object) -> DeviceKind:
        """Read a designation from an external value.

        Unknown names are rejected, not replaced with OTHER: OTHER means
        the person manually created a device of unknown designation, not
        that a typo was received in the request.

        Args:
            raw: Name of designation or its enum member.

        Returns:
            DeviceKind: Read designation.

        Raises:
            ValueError: When the value does not name a designation.
        """
        if isinstance(raw, cls):
            return raw
        if raw is None:
            raise ValueError("device kind is missing")
        return cls(str(raw).strip().upper())
