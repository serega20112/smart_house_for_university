"""Snapshot of sensor readings at a point in time."""

from __future__ import annotations

from dataclasses import dataclass

from smart_home_backend.domain.value_objects.climate.humidity import Humidity
from smart_home_backend.domain.value_objects.climate.temperature import Temperature


@dataclass(frozen=True, slots=True)
class ClimateReading:
    """Readings of the temperature and humidity sensor.

    Args:
        temperature: Measured temperature or None when unavailable.
        humidity: Measured humidity or None when unavailable.

    Returns:
        None.
    """

    temperature: Temperature | None
    humidity: Humidity | None

    @property
    def is_valid(self) -> bool:
        """Return whether at least one usable measurement is present.

        Returns:
            bool: True when the reading can drive automation.
        """
        return self.temperature is not None or self.humidity is not None
