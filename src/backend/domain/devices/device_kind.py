"""Kinds of logical device.

The kind describes what a device is for. It carries no knowledge of how a device
is named in any language: recognising the word "лампа" belongs to the language
pipeline, never to the model.
"""

from __future__ import annotations

from enum import StrEnum


class DeviceKind(StrEnum):
    """What a logical device is for."""

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
        """Read a kind from a value received from the outside.

        An unknown name is refused rather than replaced by OTHER, because OTHER
        means "the user chose to have a device of an unknown kind" and is not the
        same as "the request contained a typo".

        Args:
            raw: Kind name or enum member.

        Returns:
            DeviceKind: Parsed kind.

        Raises:
            ValueError: When the value does not name a kind.
        """
        if isinstance(raw, cls):
            return raw
        if raw is None:
            raise ValueError("device kind is missing")
        return cls(str(raw).strip().upper())
