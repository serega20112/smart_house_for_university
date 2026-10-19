"""Tests of the automation engine."""

from __future__ import annotations

import pytest

from smart_home_backend.application.services import (
    SKIP_AUTOMATION_DISABLED,
    SKIP_MANUAL_OVERRIDE,
    SKIP_NO_SENSOR_DATA,
    AutomationEngine,
    DeviceExecutor,
    HomeRuntime,
    HomeRuntimes,
)
from smart_home_backend.domain.entities.automation import AutomationSettings
from smart_home_backend.domain.enums.operation import OperationStatus
from tests.conftest import FakeEspGateway


@pytest.fixture
def runtimes(clock, owner) -> HomeRuntimes:
    registry = HomeRuntimes(clock)
    registry.for_user(owner).set_esp_online(True)
    return registry


@pytest.fixture
def runtime(runtimes: HomeRuntimes, owner) -> HomeRuntime:
    return runtimes.for_user(owner)


@pytest.fixture
def engine(esp: FakeEspGateway, runtimes: HomeRuntimes, events) -> AutomationEngine:
    return AutomationEngine(runtimes=runtimes, executor=DeviceExecutor(esp, runtimes, events))


async def test_disabled_automation_does_nothing(
    engine, automation, air_conditioner, owner
) -> None:
    settings = AutomationSettings(enabled=False)
    cycle = await engine.run_once(owner, [air_conditioner], settings)
    assert cycle.skipped_reason == SKIP_AUTOMATION_DISABLED
    assert cycle.actions == []


async def test_manual_override_suspends_automation(
    engine, automation, air_conditioner, runtime: HomeRuntime, owner
) -> None:
    runtime.set_manual_override(30)
    cycle = await engine.run_once(owner, [air_conditioner], automation)
    assert cycle.skipped_reason == SKIP_MANUAL_OVERRIDE


async def test_missing_sensor_data_suspends_automation(
    engine, automation, air_conditioner, owner
) -> None:
    cycle = await engine.run_once(owner, [air_conditioner], automation)
    assert cycle.skipped_reason == SKIP_NO_SENSOR_DATA


async def test_hot_room_starts_cooling(
    engine, automation, air_conditioner, runtime: HomeRuntime, esp: FakeEspGateway, owner
) -> None:
    runtime.apply_reading(26.0, 40.0)
    cycle = await engine.run_once(owner, [air_conditioner], automation)
    assert cycle.demands == ["COOL"]
    assert esp.commands == [(owner, 4, True)]


async def test_temperature_inside_band_changes_nothing(
    engine, automation, air_conditioner, runtime: HomeRuntime, esp: FakeEspGateway, owner
) -> None:
    runtime.apply_reading(22.0, 40.0)
    cycle = await engine.run_once(owner, [air_conditioner], automation)
    assert cycle.demands == []
    assert esp.commands == []


async def test_missing_capability_is_reported_as_unsupported(
    engine, automation, runtime: HomeRuntime, owner
) -> None:
    runtime.apply_reading(26.0, 40.0)
    cycle = await engine.run_once(owner, [], automation)
    assert cycle.actions[0].status is OperationStatus.UNSUPPORTED


async def test_only_automation_participants_are_driven(
    engine, automation, light, runtime: HomeRuntime, esp: FakeEspGateway, owner
) -> None:
    runtime.apply_reading(26.0, 40.0)
    await engine.run_once(owner, [light], automation)
    assert esp.commands == []


async def test_automation_of_one_user_ignores_another_reading(
    engine, automation, air_conditioner, runtimes: HomeRuntimes, esp: FakeEspGateway, owner,
    other_owner
) -> None:
    runtimes.for_user(other_owner).set_esp_online(True)
    runtimes.for_user(other_owner).apply_reading(26.0, 40.0)
    cycle = await engine.run_once(owner, [air_conditioner], automation)
    assert cycle.skipped_reason == SKIP_NO_SENSOR_DATA
    assert esp.commands == []
