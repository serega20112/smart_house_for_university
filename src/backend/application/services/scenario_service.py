"""Lifecycle of the timed scenarios of one home.

A scenario is a deferred promise, and this service is the only thing that keeps
them: it starts the ones whose moment has come, watches whether the goal was
reached and finishes them according to the behavior the user chose.

Two properties are worth naming. The service never receives a persistence callback,
so the repository it was built with is the only way it stores anything. And it never
holds a transaction while it talks to a board: a network round trip must not keep a
database connection checked out, which is what a slow board would otherwise do for
every scenario of every account.
"""

from __future__ import annotations

from collections.abc import Sequence
from datetime import datetime

from backend.application.dto.scenario import ScenarioView, ScheduleScenarioCommand
from backend.application.errors import ScenarioNotFoundError
from backend.application.ports.events import (
    DomainEventDispatcher,
    NotificationFactory,
    RealtimePublisher,
    UserNotifier,
)
from backend.application.ports.services import Clock, HomeStateStore
from backend.application.ports.unit_of_work.home import HomeUnitOfWorkFactory
from backend.application.services.device_control import DeviceControlService
from backend.domain.climate.home_state import HomeState
from backend.domain.climate.temperature import Temperature
from backend.domain.devices.device import Device
from backend.domain.exceptions import ScenarioAlreadyFinishedError
from backend.domain.identifiers import ScenarioId, UserId
from backend.domain.scenarios.scenario import Scenario

SCENARIO_SCHEDULED_EVENT = "scenario.scheduled"
SCENARIO_STARTED_EVENT = "scenario.started"
SCENARIO_FINISHED_EVENT = "scenario.finished"

GOAL_REACHED = "goal_reached"
DURATION_EXPIRED = "duration_expired"
CANCELLED_BY_USER = "cancelled_by_user"


class ScenarioService:
    """Schedules, advances and finishes the scenarios of a home."""

    def __init__(
        self,
        home_uow: HomeUnitOfWorkFactory,
        control: DeviceControlService,
        state_store: HomeStateStore,
        realtime: RealtimePublisher,
        dispatcher: DomainEventDispatcher,
        notifier: UserNotifier,
        notifications: NotificationFactory,
        clock: Clock,
        summary_window_sec: int,
    ) -> None:
        """Initialize the service.

        Args:
            home_uow: Factory producing transactions over the configuration.
            control: Service performing capabilities against the hardware.
            state_store: Durable home of the volatile state.
            realtime: Publisher of events to the open clients.
            dispatcher: Hands recorded facts to their subscribers.
            notifier: Delivery channel for notifications.
            notifications: Builds the wording of every message.
            clock: Source of the current time.
            summary_window_sec: Shortest interval between two progress messages of
                the same scenario.

        Returns:
            None.
        """
        self._home_uow = home_uow
        self._control = control
        self._state_store = state_store
        self._realtime = realtime
        self._dispatcher = dispatcher
        self._notifier = notifier
        self._notifications = notifications
        self._clock = clock
        self._summary_window_sec = summary_window_sec

    async def schedule(self, user_id: UserId, command: ScheduleScenarioCommand) -> ScenarioView:
        """Store a scenario waiting for its start moment.

        Args:
            user_id: Owner of the scenario.
            command: The deferred action the user asked for.

        Returns:
            ScenarioView: The stored scenario.
        """
        async with self._home_uow() as uow:
            scenario = Scenario.schedule(
                user_id=user_id,
                created_at=self._clock.now(),
                delay_minutes=command.delay_minutes,
                actions=(command.action,),
                target=command.target,
                completion_behavior=command.completion_behavior,
                duration_minutes=command.duration_minutes,
            )
            await uow.scenarios.add(scenario)
        await self._realtime.publish(user_id, SCENARIO_SCHEDULED_EVENT, _payload(scenario))
        await self._dispatcher.dispatch(scenario.pull_events())
        return _view_of(scenario)

    async def cancel(self, user_id: UserId, scenario_id: ScenarioId) -> ScenarioView:
        """Give a scenario up.

        Cancelling runs through the same path as finishing on purpose. Writing
        straight to the database would leave the hardware switched, the override
        window open and the progress messages coming, which is exactly what a user
        would call a bug.

        Args:
            user_id: Owner of the scenario.
            scenario_id: Identifier of the scenario.

        Returns:
            ScenarioView: The cancelled scenario.

        Raises:
            ScenarioNotFoundError: When the account has no such scenario.
            ScenarioAlreadyFinishedError: When the scenario already finished.
        """
        async with self._home_uow() as uow:
            scenario = await uow.scenarios.get(user_id, scenario_id)
            if scenario is None:
                raise ScenarioNotFoundError(scenario_id)
            devices = list(await uow.devices.list_all(user_id))
            scenario.cancel()
            await uow.scenarios.update(scenario)
        await self._control.restore_statuses(user_id, devices, scenario.statuses_to_restore())
        await self._realtime.publish(user_id, SCENARIO_FINISHED_EVENT, _payload(scenario))
        await self._dispatcher.dispatch(scenario.pull_events())
        await self._notifier.notify(
            user_id, self._notifications.scenario_finished(str(scenario_id), CANCELLED_BY_USER)
        )
        return _view_of(scenario)

    async def advance(self, user_id: UserId) -> None:
        """Move every scenario holding priority forward by one step.

        A scenario that cannot move on is marked as failed and the tick carries on,
        so one broken promise never stops the others.

        Args:
            user_id: Owner of the scenarios.

        Returns:
            None.
        """
        async with self._home_uow() as uow:
            scenarios = list(await uow.scenarios.list_holding_priority(user_id))
            devices = list(await uow.devices.list_all(user_id))
        state = await self._state_store.load(user_id)
        now = self._clock.now()
        for scenario in scenarios:
            try:
                await self._advance_one(scenario, devices, state, now)
            except ScenarioAlreadyFinishedError:
                continue

    async def _advance_one(
        self,
        scenario: Scenario,
        devices: Sequence[Device],
        state: HomeState,
        now: datetime,
    ) -> None:
        if scenario.is_due(now):
            await self._start(scenario, devices, state)
            return
        if scenario.is_goal_reached(state.reading):
            await self._finish(scenario, devices, GOAL_REACHED)
            return
        if scenario.has_timed_out(now):
            await self._finish(scenario, devices, DURATION_EXPIRED)
            return
        await self._report_progress(scenario, state.reading.temperature)

    async def _start(
        self,
        scenario: Scenario,
        devices: Sequence[Device],
        state: HomeState,
    ) -> None:
        captured = {device.id: state.status_of(device) for device in devices}
        async with self._home_uow() as uow:
            scenario.start(captured)
            await uow.scenarios.update(scenario)
        for action in scenario.actions:
            await self._control.apply_to_first_matching(
                scenario.user_id, devices, action.capability, manual=False
            )
        await self._realtime.publish(
            scenario.user_id, SCENARIO_STARTED_EVENT, _payload(scenario)
        )
        await self._dispatcher.dispatch(scenario.pull_events())
        await self._notifier.notify(
            scenario.user_id,
            self._notifications.scenario_started(str(scenario.id), scenario.target),
        )

    async def _finish(
        self, scenario: Scenario, devices: Sequence[Device], reason: str
    ) -> None:
        async with self._home_uow() as uow:
            scenario.complete(reason)
            await uow.scenarios.update(scenario)
        await self._control.restore_statuses(
            scenario.user_id, devices, scenario.statuses_to_restore()
        )
        await self._realtime.publish(
            scenario.user_id, SCENARIO_FINISHED_EVENT, _payload(scenario)
        )
        await self._dispatcher.dispatch(scenario.pull_events())
        await self._notifier.notify(
            scenario.user_id, self._notifications.scenario_finished(str(scenario.id), reason)
        )

    async def _report_progress(
        self, scenario: Scenario, temperature: Temperature | None
    ) -> None:
        allowed = await self._state_store.claim_summary_slot(
            scenario.user_id, f"scenario:{scenario.id}", self._summary_window_sec
        )
        if not allowed:
            return
        await self._notifier.notify(
            scenario.user_id,
            self._notifications.scenario_progress(
                str(scenario.id), None if temperature is None else temperature.celsius
            ),
        )


def _view_of(scenario: Scenario) -> ScenarioView:
    return ScenarioView(
        id=scenario.id,
        status=scenario.status,
        created_at=scenario.created_at,
        start_at=scenario.start_at,
        duration_minutes=scenario.duration_minutes,
        target=scenario.target,
        completion_behavior=scenario.completion_behavior,
        actions=scenario.actions,
    )


def _payload(scenario: Scenario) -> dict[str, object]:
    first = scenario.actions[0] if scenario.actions else None
    return {
        "scenario_id": str(scenario.id),
        "status": scenario.status.value,
        "target": scenario.target,
        "capability": None if first is None else first.capability.value,
        "target_temperature": (
            None
            if first is None or first.target_temperature is None
            else first.target_temperature.celsius
        ),
        "completion_behavior": scenario.completion_behavior.value,
    }
