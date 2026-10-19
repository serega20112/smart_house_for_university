"""Kind of component a dashboard widget renders."""

from __future__ import annotations

from enum import StrEnum


class WidgetKind(StrEnum):
    """A generic component the interface already knows how to draw.

    Args:
        None.

    Returns:
        None.
    """

    CLIMATE = "climate"
    SENSOR = "sensor"
    DEVICE = "device"
    COMMAND = "command"

    @classmethod
    def parse(cls, raw: object) -> WidgetKind:
        """Read a widget kind from a value received from the outside.

        Args:
            raw: Widget kind name or enum member.

        Returns:
            WidgetKind: Parsed kind.

        Raises:
            ValueError: When the value does not name a widget kind.
        """
        if isinstance(raw, cls):
            return raw
        if raw is None:
            raise ValueError("widget kind is missing")
        return cls(str(raw).strip().lower())
