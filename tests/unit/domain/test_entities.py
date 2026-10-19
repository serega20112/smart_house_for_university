"""Tests of the domain entities and value objects."""

from __future__ import annotations

from datetime import timedelta

import pytest

from smart_home_backend.domain.entities.scenario import Scenario, ScenarioAction
from smart_home_backend.domain.enums.device import Capability, DeviceType
from smart_home_backend.domain.enums.scenario import CompletionBehavior, ScenarioStatus
from smart_home_backend.domain.exceptions import UnsupportedCapabilityError
from smart_home_backend.domain.value_objects.climate import ClimateRange, Humidity, Temperature
from tests.conftest import BASE_TIME


def test_device_rejects_unsupported_capability(light) -> None:
    with pytest.raises(UnsupportedCapabilityError):
        light.require(Capability.COOL)


def test_device_accepts_supported_capability(light) -> None:
    light.require(Capability.ON)


def test_participation_requires_both_flags(air_conditioner: object) -> None:
    assert air_conditioner.is_participating_in_automation is True
    air_conditioner.automation_enabled = False
    assert air_conditioner.is_participating_in_automation is False


def test_status_can_be_attached_without_mutating_configuration(light) -> None:
    from smart_home_backend.domain.enums.device import DeviceStatus

    snapshot = light.with_status(DeviceStatus.UNAVAILABLE)
    assert snapshot.status is DeviceStatus.UNAVAILABLE
    assert light.type is DeviceType.LIGHT


def test_temperature_rejects_impossible_value() -> None:
    with pytest.raises(ValueError):
        Temperature(120.0)


def test_humidity_is_clamped_on_shift() -> None:
    assert Humidity(95.0).with_delta(20.0).percent == 100.0


def test_range_bounds_use_absolute_tolerance() -> None:
    climate_range = ClimateRange(target=22.0, tolerance=-1.0)
    assert climate_range.low == 21.0
    assert climate_range.high == 23.0


def test_scenario_starts_when_moment_comes(clock) -> None:
    scenario = Scenario(
        id=1,
        status=ScenarioStatus.PENDING,
        created_at=BASE_TIME,
        start_at=BASE_TIME,
        duration_minutes=30,
    )
    assert scenario.should_start(clock.now()) is True
    assert scenario.is_expired(clock.now()) is False


def test_scenario_expires_after_duration(clock) -> None:
    scenario = Scenario(
        id=1,
        status=ScenarioStatus.RUNNING,
        created_at=BASE_TIME,
        start_at=BASE_TIME,
        duration_minutes=30,
    )
    assert scenario.is_expired(clock.now() + timedelta(minutes=31))


def test_scenario_action_round_trip() -> None:
    action = ScenarioAction(Capability.COOL, 20.0)
    assert ScenarioAction.from_dict(action.to_dict()) == action


def test_completion_behavior_default_continues_automation(clock) -> None:
    scenario = Scenario(
        id=1,
        status=ScenarioStatus.PENDING,
        created_at=BASE_TIME,
        start_at=BASE_TIME,
    )
    assert scenario.completion_behavior is CompletionBehavior.CONTINUE_AUTOMATION
