"""Tests of the climate policy."""

from __future__ import annotations

from smart_home_backend.domain.entities.automation import AutomationSettings
from smart_home_backend.domain.entities.home import ClimateReading
from smart_home_backend.domain.enums.device import Capability
from smart_home_backend.domain.policies import (
    ClimateDemand,
    capability_for_target,
    evaluate,
    evaluate_temperature,
)
from smart_home_backend.domain.value_objects.climate import Humidity, Temperature


def reading(temperature: float | None, humidity: float | None = 40.0) -> ClimateReading:
    return ClimateReading(
        temperature=None if temperature is None else Temperature(temperature),
        humidity=None if humidity is None else Humidity(humidity),
    )


def test_temperature_inside_band_requires_nothing(automation: AutomationSettings) -> None:
    assert evaluate_temperature(automation, reading(22.4)) is ClimateDemand.NONE


def test_temperature_above_band_demands_cooling(automation: AutomationSettings) -> None:
    assert evaluate_temperature(automation, reading(26.0)) is ClimateDemand.COOL


def test_temperature_below_band_demands_heating(automation: AutomationSettings) -> None:
    assert evaluate_temperature(automation, reading(17.0)) is ClimateDemand.HEAT


def test_band_edges_do_not_trigger_switching(automation: AutomationSettings) -> None:
    assert evaluate_temperature(automation, reading(21.0)) is ClimateDemand.NONE
    assert evaluate_temperature(automation, reading(23.0)) is ClimateDemand.NONE


def test_missing_temperature_produces_no_demand(automation: AutomationSettings) -> None:
    assert evaluate_temperature(automation, reading(None)) is ClimateDemand.NONE


def test_low_humidity_demands_humidification(automation: AutomationSettings) -> None:
    settings = AutomationSettings(target_humidity=45.0, humidity_tolerance=5.0)
    assert ClimateDemand.HUMIDIFY in evaluate(settings, reading(22.0, 20.0))


def test_humidity_demand_maps_to_capability(automation: AutomationSettings) -> None:
    assert ClimateDemand.HUMIDIFY.capability is Capability.ON
    assert ClimateDemand.COOL.capability is Capability.COOL
    assert ClimateDemand.NONE.capability is None


def test_target_below_current_asks_for_cooling() -> None:
    assert capability_for_target(26.0, 20.0) is Capability.COOL


def test_target_above_current_asks_for_heating() -> None:
    assert capability_for_target(18.0, 22.0) is Capability.HEAT


def test_target_without_reading_defaults_to_cooling() -> None:
    assert capability_for_target(None, 20.0) is Capability.COOL
