"""Snapshot of the climate sensors at a point in time."""

from __future__ import annotations

from dataclasses import dataclass

from backend.domain.value_objects.climate.humidity import Humidity
from backend.domain.value_objects.climate.temperature import Temperature


@dataclass(frozen=True, slots=True)
class ClimateReading:
    """What the sensors reported last.

    A field is absent rather than zero when the board could not measure it, so
    automation can tell "the room is exactly zero degrees" from "the sensor did
    not answer".

    Args:
        temperature: Measured temperature or None when unavailable.
        humidity: Measured relative humidity or None when unavailable.

    Returns:
        None.
    """

    temperature: Temperature | None = None
    humidity: Humidity | None = None

    @property
    def is_usable(self) -> bool:
        """Return whether at least one usable measurement is present.

        Returns:
            bool: True when the reading can drive automation.
        """
        return self.temperature is not None or self.humidity is not None

    @classmethod
    def measured(cls, celsius: float | None, percent: float | None) -> ClimateReading:
        """Build a reading from raw sensor numbers.

        Args:
            celsius: Measured temperature or None.
            percent: Measured relative humidity or None.

        Returns:
            ClimateReading: Typed reading.
        """
        return cls(
            temperature=None if celsius is None else Temperature(celsius),
            humidity=None if percent is None else Humidity(percent),
        )
