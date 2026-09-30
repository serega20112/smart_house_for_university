"""Physical sensor entity."""

from __future__ import annotations

from dataclasses import dataclass

from smart_home_backend.domain.entities.home.climate_reading import ClimateReading
from smart_home_backend.domain.value_objects.climate.humidity import Humidity
from smart_home_backend.domain.value_objects.climate.temperature import Temperature


@dataclass(frozen=True, slots=True)
class Sensor:
    """Raw sensor values reported by the board.

    Args:
        temperature_celsius: Measured temperature or None when unavailable.
        humidity_percent: Measured humidity or None when unavailable.

    Returns:
        None.
    """

    temperature_celsius: float | None
    humidity_percent: float | None

    def to_reading(self) -> ClimateReading:
        """Convert raw values into typed value objects.

        Returns:
            ClimateReading: Typed reading.
        """
        temperature = (
            Temperature(self.temperature_celsius) if self.temperature_celsius is not None else None
        )
        humidity = Humidity(self.humidity_percent) if self.humidity_percent is not None else None
        return ClimateReading(temperature=temperature, humidity=humidity)
