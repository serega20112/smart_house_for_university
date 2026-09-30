"""Automation settings entity."""

from __future__ import annotations

from dataclasses import dataclass

from smart_home_backend.domain.value_objects.climate.climate_range import ClimateRange

MIN_TEMPERATURE_C = -10.0
MAX_TEMPERATURE_C = 45.0
MIN_HUMIDITY_PERCENT = 0.0
MAX_HUMIDITY_PERCENT = 100.0


@dataclass
class AutomationSettings:
    """Parameters of the climate automation mode.

    Targets are stored together with a tolerance, which forms the hysteresis
    band that keeps devices from switching around the target value.

    Args:
        enabled: Whether automation is active.
        target_temperature: Target temperature in degrees Celsius.
        temperature_tolerance: Allowed temperature deviation in degrees Celsius.
        target_humidity: Target relative humidity in percent.
        humidity_tolerance: Allowed humidity deviation in percent.
        participating_device_ids: Devices taking part in automation; empty means
            every device with the automation flag enabled.

    Returns:
        None.
    """

    enabled: bool = False

    target_temperature: float = 22.0
    temperature_tolerance: float = 1.0

    target_humidity: float = 45.0
    humidity_tolerance: float = 5.0

    participating_device_ids: frozenset[int] = frozenset()

    def temperature_range(self) -> ClimateRange:
        """Return the acceptable temperature band.

        Returns:
            ClimateRange: Temperature band around the target.
        """
        return ClimateRange(self.target_temperature, self.temperature_tolerance)

    def humidity_range(self) -> ClimateRange:
        """Return the acceptable humidity band.

        Returns:
            ClimateRange: Humidity band around the target.
        """
        return ClimateRange(self.target_humidity, self.humidity_tolerance)

    def device_participates(self, device_id: int) -> bool:
        """Return whether a device is allowed to be driven by automation.

        Args:
            device_id: Identifier of the device.

        Returns:
            bool: True when the device participates in automation.
        """
        if not self.participating_device_ids:
            return True
        return device_id in self.participating_device_ids
