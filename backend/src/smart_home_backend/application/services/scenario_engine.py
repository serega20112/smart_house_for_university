"""Scenario engine driving timed tasks.

A scenario is a deferred action such as "make it 20 degrees in half an hour".
Each tick starts the scenarios whose moment has come, watches whether the climate
goal is reached and finishes them according to the completion behavior. Only
significant moments produce notifications.

A running scenario outranks automation, which is expressed through the manual
override window opened when a scenario starts.
"""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from datetime import datetime, timedelta
from typing import Any

from smart_home_backend.application.interface.services import Clock, EventBus, Notifier
from smart_home_backend.application.services import notifications
from smart_home_backend.application.services.device_executor import DeviceExecutor
from smart_home_backend.application.services.home_runtime import HomeRuntime
from smart_home_backend.domain.entities.device import Device
from smart_home_backend.domain.entities.scenario import Scenario, ScenarioAction
from smart_home_backend.domain.enums.device import Capability, DeviceStatus
from smart_home_backend.domain.enums.scenario import CompletionBehavior, ScenarioStatus
from smart_home_backend.domain.policies import has_timed_out, is_goal_reached
from smart_home_backend.domain.value_objects.device import DeviceState

PersistScenario = Callable[[Scenario], Awaitable[Scenario]]


class ScenarioEngine:
    """Lifecycle of the timed scenarios."""

    def __init__(
        self,
        runtime: HomeRuntime,
        executor: DeviceExecutor,
        events: EventBus,
        notifier: Notifier,
        clock: Clock,
        manual_override_minutes: int = 30,
        summary_minutes: int = 10,
    ) -> None:
        """Initialize the engine.

        Args:
            runtime: Runtime state holding the current reading.
            executor: Executor performing the capability commands.
            events: Publisher of realtime events.
            notifier: Delivery channel for significant events.
            clock: Clock used for scheduling.
            manual_override_minutes: How long a scenario suspends automation.
            summary_minutes: Interval between progress notifications.

        Returns:
            None.
        """
        self._runtime = runtime
        self._executor = executor
        self._events = events
        self._notifier = notifier
        self._clock = clock
        self._manual_override_minutes = manual_override_minutes
        self._summary_minutes = summary_minutes
        self._last_summary_at: dict[int, datetime] = {}

    async def create(
        self,
        delay_minutes: int | None,
        capability: Capability | None,
        target_temperature: float | None,
        target: str | None,
        completion_behavior: CompletionBehavior,
        persist: PersistScenario,
    ) -> Scenario:
        """Create a pending scenario.

        Args:
            delay_minutes: Delay before the scenario starts acting.
            capability: Capability to perform, or None for an empty scenario.
            target_temperature: Target temperature of the action.
            target: Target area or object taken from the user command.
            completion_behavior: What happens with devices after completion.
            persist: Callable persisting the scenario.

        Returns:
            Scenario: Stored scenario including its identifier.
        """
        now = self._clock.now()
        delay = delay_minutes if delay_minutes and delay_minutes > 0 else 0
        actions: list[ScenarioAction] = []
        if capability is not None:
            actions.append(ScenarioAction(capability, target_temperature))
        scenario = Scenario(
            id=0,
            status=ScenarioStatus.PENDING,
            created_at=now,
            start_at=now + timedelta(minutes=delay),
            actions=actions,
            target=target,
            duration_minutes=delay_minutes,
            completion_behavior=completion_behavior,
        )
        stored = await persist(scenario)
        await self._events.publish("scenario.created", scenario_payload(stored))
        return stored

    async def tick(
        self,
        active: list[Scenario],
        devices: list[Device],
        persist: PersistScenario,
    ) -> None:
        """Advance every active scenario by one step.

        A failing scenario is marked as failed without interrupting the tick, so
        one broken task never stops the others.

        Args:
            active: Pending and running scenarios.
            devices: Configured devices.
            persist: Callable persisting a scenario.

        Returns:
            None.
        """
        for scenario in active:
            try:
                await self._advance(scenario, devices, persist)
            except Exception as exc:
                await self._fail(scenario, exc, persist)

    async def _advance(
        self, scenario: Scenario, devices: list[Device], persist: PersistScenario
    ) -> None:
        if scenario.should_start(self._clock.now()):
            await self._start(scenario, devices, persist)
        elif scenario.status is ScenarioStatus.RUNNING:
            await self._check_completion(scenario, devices, persist)

    async def _start(
        self, scenario: Scenario, devices: list[Device], persist: PersistScenario
    ) -> None:
        scenario.restore_snapshot = {
            device.id: self._runtime.device_status(device).value for device in devices
        }
        scenario.status = ScenarioStatus.RUNNING
        await persist(scenario)
        self._runtime.set_manual_override(self._manual_override_minutes)

        for action in scenario.actions:
            result = await self._executor.apply_first_matching(devices, action.capability)
            if not result.ok:
                await self._fail(scenario, result.status.value, persist)
                return

        await self._events.publish("scenario.started", scenario_payload(scenario))
        await self._notifier.notify(notifications.scenario_started(scenario))

    async def _check_completion(
        self, scenario: Scenario, devices: list[Device], persist: PersistScenario
    ) -> None:
        now = self._clock.now()
        temperature = self._runtime.state.temperature
        if is_goal_reached(scenario, temperature):
            await self._complete(scenario, devices, persist, notifications.GOAL_REACHED)
            return
        if has_timed_out(scenario, now):
            await self._complete(scenario, devices, persist, notifications.DURATION_EXPIRED)
            return
        await self._send_summary(scenario, temperature, now)

    async def _send_summary(
        self, scenario: Scenario, temperature: float | None, now: datetime
    ) -> None:
        last = self._last_summary_at.get(scenario.id)
        if last is not None and now - last < timedelta(minutes=self._summary_minutes):
            return
        self._last_summary_at[scenario.id] = now
        await self._notifier.notify(notifications.scenario_summary(scenario, temperature))

    async def _complete(
        self,
        scenario: Scenario,
        devices: list[Device],
        persist: PersistScenario,
        reason: str,
    ) -> None:
        await self._apply_completion(scenario, devices)
        scenario.status = ScenarioStatus.COMPLETED
        await persist(scenario)
        self._last_summary_at.pop(scenario.id, None)
        await self._events.publish("scenario.completed", scenario_payload(scenario))
        await self._notifier.notify(notifications.scenario_completed(scenario, reason))

    async def _apply_completion(self, scenario: Scenario, devices: list[Device]) -> None:
        behavior = scenario.completion_behavior
        if behavior is CompletionBehavior.CONTINUE_AUTOMATION:
            return
        if behavior is CompletionBehavior.OFF:
            active_ids = [
                device.id
                for device in devices
                if DeviceState(self._runtime.device_status(device)).is_active
            ]
            await self._executor.restore_statuses(
                devices, {device_id: DeviceStatus.OFF for device_id in active_ids}
            )
            return
        if behavior is CompletionBehavior.RESTORE_PREVIOUS_STATE:
            await self._executor.restore_statuses(devices, _statuses_of(scenario))

    async def _fail(
        self, scenario: Scenario, reason: object, persist: PersistScenario
    ) -> None:
        scenario.status = ScenarioStatus.FAILED
        await persist(scenario)
        self._last_summary_at.pop(scenario.id, None)
        await self._events.publish(
            "scenario.failed", {**scenario_payload(scenario), "reason": str(reason)}
        )
        await self._notifier.notify(notifications.scenario_failed(scenario, str(reason)))


def scenario_payload(scenario: Scenario) -> dict[str, Any]:
    """Return the realtime payload describing a scenario.

    Args:
        scenario: Scenario to describe.

    Returns:
        dict[str, Any]: Serializable payload.
    """
    return {
        "scenario_id": scenario.id,
        "status": scenario.status.value,
        "target": scenario.target,
        "actions": [action.to_dict() for action in scenario.actions],
    }


def _statuses_of(scenario: Scenario) -> dict[int, DeviceStatus]:
    statuses: dict[int, DeviceStatus] = {}
    for device_id, status_value in scenario.restore_snapshot.items():
        try:
            statuses[device_id] = DeviceStatus(status_value)
        except ValueError:
            continue
    return statuses
