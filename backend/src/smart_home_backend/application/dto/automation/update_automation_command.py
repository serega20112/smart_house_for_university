"""Command that updates the automation settings."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class UpdateAutomationCommand:
    """Input of the automation settings update use case.

    Every field is optional, so an empty command leaves the settings unchanged.

    Args:
        enabled: Whether the automation mode is active.
        target_temperature: Target temperature in degrees Celsius.
        temperature_tolerance: Allowed temperature deviation in degrees Celsius.
        target_humidity: Target relative humidity in percent.
        humidity_tolerance: Allowed humidity deviation in percent.
        participating_device_ids: Devices taking part in automation.

    Returns:
        None.
    """

    enabled: bool | None = None
    target_temperature: float | None = None
    temperature_tolerance: float | None = None
    target_humidity: float | None = None
    humidity_tolerance: float | None = None
    participating_device_ids: list[int] | None = None
