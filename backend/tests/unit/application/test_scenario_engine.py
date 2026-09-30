"""Tests of the scenario engine."""

from __future__ import annotations

from datetime import timedelta

import pytest

from smart_home_backend.application.interface.services import CommandOutcome
from smart_home_backend.application.services import (
    DeviceExecutor,
    HomeRuntime,
    ScenarioEngine,
)
from smart_home_backend.domain.entities.scenario import Scenario, ScenarioAction
from smart_home_backend.domain.enums.device import Capability, DeviceStatus
from smart_home_backend.domain.enums.scenario import CompletionBehavior, ScenarioStatus

from tests.conftest import BASE_TIME, FakeEspGateway


@pytest.fixture
def runtime(clock) -> HomeRuntime:
    state = HomeRuntime(clock)
    state.set_esp_online(True)
    return state


def build_engine(clock, esp, runtime, events, notifier) -> ScenarioEngine:
    return ScenarioEngine(
        runtime=runtime,
        executor=DeviceExecutor(esp, runtime, events),
        events=events,
        notifier=notifier,
        clock=clock,
        manual_override_minutes=30,
        summary_minutes=10,
    )


@pytest.fixture
def engine(clock, esp, runtime, events, notifier) -> ScenarioEngine:
    return build_engine(clock, esp, runtime, events, notifier)


async def persist(scenario: Scenario) -> Scenario:
    scenario.id = scenario.id or 1
    return scenario


def scenario(**kwargs) -> Scenario:
    defaults = {
        "id": 1,
        "status": ScenarioStatus.PENDING,
        "created_at": BASE_TIME,
        "start_at": BASE_TIME,
    }
    return Scenario(**{**defaults, **kwargs})


async def test_scenario_is_created_pending(engine) -> None:
    created = await engine.create(
        delay_minutes=30,
        capability=Capability.COOL,
        target_temperature=20.0,
        target="room",
        completion_behavior=CompletionBehavior.CONTINUE_AUTOMATION,
        persist=persist,
    )
    assert created.status is ScenarioStatus.PENDING
    assert created.actions[0].target_value == 20.0


async def test_creation_is_published(engine, events) -> None:
    await engine.create(30, Capability.COOL, 20.0, None, CompletionBehavior.OFF, persist)
    assert events.types() == ["scenario.created"]


async def test_pending_scenario_waits_for_its_moment(engine, air_conditioner) -> None:
    pending = scenario(start_at=BASE_TIME + timedelta(minutes=30))
    await engine.tick([pending], [air_conditioner], persist)
    assert pending.status is ScenarioStatus.PENDING


async def test_due_scenario_starts_and_suspends_automation(
    engine, air_conditioner, runtime: HomeRuntime, esp: FakeEspGateway, notifier
) -> None:
    due = scenario(actions=[ScenarioAction(Capability.COOL, 20.0)])
    await engine.tick([due], [air_conditioner], persist)
    assert due.status is ScenarioStatus.RUNNING
    assert esp.commands == [(4, True)]
    assert runtime.is_manual_override() is True
    assert notifier.messages


async def test_reached_goal_completes_the_scenario(
    engine, runtime: HomeRuntime, air_conditioner, notifier
) -> None:
    running = scenario(status=ScenarioStatus.RUNNING, actions=[ScenarioAction(Capability.COOL, 20.0)])
    runtime.apply_reading(20.0, 40.0)
    await engine.tick([running], [air_conditioner], persist)
    assert running.status is ScenarioStatus.COMPLETED
    assert notifier.messages


async def test_elapsed_duration_completes_the_scenario(
    engine, runtime: HomeRuntime, air_conditioner
) -> None:
    running = scenario(
        status=ScenarioStatus.RUNNING,
        created_at=BASE_TIME - timedelta(hours=1),
        start_at=BASE_TIME - timedelta(minutes=31),
        duration_minutes=30,
        actions=[ScenarioAction(Capability.COOL, 20.0)],
    )
    runtime.apply_reading(26.0, 40.0)
    await engine.tick([running], [air_conditioner], persist)
    assert running.status is ScenarioStatus.COMPLETED


async def test_failing_action_marks_the_scenario_failed(
    clock, runtime: HomeRuntime, events, notifier, air_conditioner
) -> None:
    offline = FakeEspGateway(CommandOutcome(ok=False, error="esp_offline"))
    engine = build_engine(clock, offline, runtime, events, notifier)
    due = scenario(actions=[ScenarioAction(Capability.COOL, 20.0)])
    await engine.tick([due], [air_conditioner], persist)
    assert due.status is ScenarioStatus.FAILED


async def test_completion_turns_active_devices_off(
    engine, runtime: HomeRuntime, air_conditioner
) -> None:
    expired = scenario(
        status=ScenarioStatus.RUNNING,
        completion_behavior=CompletionBehavior.OFF,
        duration_minutes=30,
        start_at=BASE_TIME - timedelta(minutes=31),
    )
    runtime.apply_relay(air_conditioner.physical_channel, True)
    runtime.remember_mode(air_conditioner, DeviceStatus.COOL)
    await engine.tick([expired], [air_conditioner], persist)
    assert expired.status is ScenarioStatus.COMPLETED
    assert runtime.device_status(air_conditioner) is DeviceStatus.OFF


async def test_completion_can_restore_previous_states(
    engine, runtime: HomeRuntime, air_conditioner
) -> None:
    expired = scenario(
        status=ScenarioStatus.RUNNING,
        completion_behavior=CompletionBehavior.RESTORE_PREVIOUS_STATE,
        duration_minutes=30,
        start_at=BASE_TIME - timedelta(minutes=31),
        restore_snapshot={air_conditioner.id: DeviceStatus.OFF.value},
    )
    runtime.apply_relay(air_conditioner.physical_channel, True)
    runtime.remember_mode(air_conditioner, DeviceStatus.COOL)
    await engine.tick([expired], [air_conditioner], persist)
    assert runtime.device_status(air_conditioner) is DeviceStatus.OFF


async def test_completion_can_leave_devices_to_automation(
    engine, runtime: HomeRuntime, air_conditioner, esp: FakeEspGateway
) -> None:
    expired = scenario(
        status=ScenarioStatus.RUNNING,
        completion_behavior=CompletionBehavior.CONTINUE_AUTOMATION,
        duration_minutes=30,
        start_at=BASE_TIME - timedelta(minutes=31),
    )
    runtime.apply_relay(air_conditioner.physical_channel, True)
    runtime.remember_mode(air_conditioner, DeviceStatus.COOL)
    await engine.tick([expired], [air_conditioner], persist)
    assert expired.status is ScenarioStatus.COMPLETED
    assert esp.commands == []
    assert runtime.device_status(air_conditioner) is DeviceStatus.COOL
