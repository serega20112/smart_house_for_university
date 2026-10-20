"""Lifecycle of the timed scenarios of one home.

A scenario is a deferred promise, and this service is the only thing that keeps
them: it starts the ones whose moment has come, watches whether the goal was
reached and finishes them according to the behavior the user chose.

Two properties are worth naming. The service never receives a persistence callback,
so the repository it was built with is the only way it stores anything. And it never
holds a transaction while it talks to a board: a network round trip must not keep a
database connection checked out, which is what a slow board would otherwise do for
every scenario of every account.

Failures stay with the scenario that caused them. An expected refusal of the
application — a capability nothing in the home supports, a board that stopped
answering — throws a scenario into FAILED and the tick carries on, so one broken
promise never stops the others. What never worked is not recorded as done: the
commands are performed first and the aggregate is written back after they
succeeded, and a partial start puts the devices it already switched back into the
states they had before.
"""

from __future__ import annotations

from collections.abc import Sequence
from datetime import datetime

from smart_home.application.dto.scenario import ScenarioView, ScheduleScenarioCommand
from smart_home.application.errors import (
    BoardUnreachableError,
    ConcurrentModificationError,
    ScenarioNotFoundError,
)
from smart_home.application.ports.events import (
    DomainEventDispatcher,
    NotificationFactory,
    RealtimePublisher,
    UserNotifier,
)
from smart_home.application.ports.services import Clock, HomeStateStore
from smart_home.application.ports.unit_of_work.home import HomeUnitOfWorkFactory
from smart_home.application.services.device_control import DeviceControlService
from smart_home.domain.climate.home_state import HomeState
from smart_home.domain.climate.temperature import Temperature
from smart_home.domain.devices.device import Device
from smart_home.domain.devices.device_status import DeviceStatus
from smart_home.domain.exceptions import (
    NoDeviceForCapabilityError,
    ScenarioAlreadyFinishedError,
)
from smart_home.domain.identifiers import DeviceId, ScenarioId, UserId
from smart_home.domain.scenarios.finish_reason import FinishReason
from smart_home.domain.scenarios.scenario import Scenario

SCENARIO_SCHEDULED_EVENT = "scenario.scheduled"
SCENARIO_STARTED_EVENT = "scenario.started"
SCENARIO_FINISHED_EVENT = "scenario.finished"

EXPECTED_REFUSALS: tuple[type[Exception], ...] = (
    NoDeviceForCapabilityError,
    BoardUnreachableError,
)


def _reason_of(refusal: Exception) -> FinishReason:
    """Name the vocabulary entry an expected refusal corresponds to.

    Args:
        refusal: Refusal the scenario died from.

    Returns:
        FinishReason: Reason recorded on the scenario.
    """
    if isinstance(refusal, BoardUnreachableError):
        return FinishReason.BOARD_UNREACHABLE
    return FinishReason.NO_DEVICE_FOR_CAPABILITY


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
            user_id,
            self._notifications.scenario_finished(
                str(scenario_id), FinishReason.CANCELLED_BY_USER.value
            ),
        )
        return _view_of(scenario)

    async def advance(self, user_id: UserId) -> None:
        """Move every scenario holding priority forward by one step.

        A scenario that cannot move on is marked as failed and the tick carries
        on, so one broken promise never stops the others. A scenario that lost a
        race against an API call of the same tick is skipped: the next tick reads
        the fresh snapshot and sees the truth of the row.

        Args:
            user_id: Owner of the scenarios.

        Returns:
            None.
        """
        async with self._home_uow() as uow:
            scenarios = list(await uow.scenarios.list_holding_priority(user_id))
            devices = list(await uow.devices.list_all(user_id))
        state = await self._state_store.read(user_id)
        now = self._clock.now()
        for scenario in scenarios:
            try:
                await self._advance_one(scenario, devices, state, now)
            except ScenarioAlreadyFinishedError:
                continue
            except ConcurrentModificationError:
                continue
            except EXPECTED_REFUSALS as refusal:
                await self._fail(scenario, devices, _reason_of(refusal))

    async def _advance_one(
        self,
        scenario: Scenario,
        devices: Sequence[Device],
        state: HomeState,
        now: datetime,
    ) -> None:
        """Move one scenario forward by one step.

        Args:
            scenario: Scenario sitting at its current stage.
            devices: Devices the commands of the scenario address.
            state: What the home looks like right now.
            now: Moment of the tick.

        Returns:
            None.
        """
        if scenario.is_due(now):
            await self._start(scenario, devices, state)
            return
        if scenario.is_goal_reached(state.reading):
            await self._finish(scenario, devices, FinishReason.GOAL_REACHED)
            return
        if scenario.has_timed_out(now):
            await self._finish(scenario, devices, FinishReason.DURATION_EXPIRED)
            return
        await self._report_progress(scenario, state.reading.temperature)

    async def _start(
        self,
        scenario: Scenario,
        devices: Sequence[Device],
        state: HomeState,
    ) -> None:
        """Begin acting on the home, recording the start only after it worked.

        The states of the devices are captured before anything is driven, so the
        restore behaviour knows exactly what it is returning to. The aggregate is
        written back after every command was accepted: a board that refuses
        leaves the scenario pending rather than running nothing.

        Args:
            scenario: Scenario whose start moment has come.
            devices: Devices the commands of the scenario address.
            state: What the home looked like right before the commands.

        Returns:
            None.
        """
        captured = {device.id: state.status_of(device) for device in devices}
        try:
            await self._perform_actions(scenario, devices)
        except EXPECTED_REFUSALS as refusal:
            await self._undo_started_devices(scenario, devices, captured)
            raise refusal
        async with self._home_uow() as uow:
            scenario.start(captured)
            await uow.scenarios.update(scenario)
        await self._realtime.publish(scenario.user_id, SCENARIO_STARTED_EVENT, _payload(scenario))
        await self._dispatcher.dispatch(scenario.pull_events())
        await self._notifier.notify(
            scenario.user_id,
            self._notifications.scenario_started(str(scenario.id), scenario.target),
        )

    async def _perform_actions(self, scenario: Scenario, devices: Sequence[Device]) -> None:
        """Perform the commands of a scenario against the hardware.

        Args:
            scenario: Scenario the actions belong to.
            devices: Devices the commands address.

        Returns:
            None.
        """
        for action in scenario.actions:
            await self._control.apply_to_first_matching(
                scenario.user_id, devices, action.capability, manual=False
            )

    async def _undo_started_devices(
        self,
        scenario: Scenario,
        devices: Sequence[Device],
        captured: dict[DeviceId, DeviceStatus],
    ) -> None:
        """Put the devices a partial start already switched back.

        The board is refusing right now, which is what made the scenario fail,
        so the undo is best effort: whatever the board does accept is restored,
        and what it does not is left to one of the following worker passes.

        Args:
            scenario: Owner of the states to restore.
            devices: Devices the commands addressed.
            captured: States the devices had before the scenario acted.

        Returns:
            None.
        """
        wanted = _restorable(captured)
        if not wanted:
            return
        try:
            await self._control.restore_statuses(scenario.user_id, devices, wanted)
        except EXPECTED_REFUSALS:
            return

    async def _finish(
        self, scenario: Scenario, devices: Sequence[Device], reason: FinishReason
    ) -> None:
        """Stop a scenario on purpose and put the devices back.

        Args:
            scenario: Scenario whose stage changes to a terminal one.
            devices: Devices the commands of the scenario address.
            reason: Why the scenario stopped acting.

        Returns:
            None.
        """
        async with self._home_uow() as uow:
            scenario.complete(reason.value)
            await uow.scenarios.update(scenario)
        await self._control.restore_statuses(
            scenario.user_id, devices, scenario.statuses_to_restore()
        )
        await self._realtime.publish(scenario.user_id, SCENARIO_FINISHED_EVENT, _payload(scenario))
        await self._dispatcher.dispatch(scenario.pull_events())
        await self._notifier.notify(
            scenario.user_id,
            self._notifications.scenario_finished(str(scenario.id), reason.value),
        )

    async def _fail(
        self,
        scenario: Scenario,
        devices: Sequence[Device],
        reason: FinishReason,
    ) -> None:
        """Record that a scenario could not be carried out.

        Devices the scenario managed to switch before the refusal are put back
        into the states they had before, so a failed scenario leaves nothing
        behind except the record of why. The undo itself is best effort, because
        the board that caused the failure may still be refusing.

        Args:
            scenario: Scenario whose carrying out did not work.
            devices: Devices the commands of the scenario address.
            reason: Why the scenario stopped acting.

        Returns:
            None.
        """
        try:
            scenario.fail(reason.value)
        except ScenarioAlreadyFinishedError:
            return
        async with self._home_uow() as uow:
            await uow.scenarios.update(scenario)
        await self._control.restore_statuses(
            scenario.user_id, devices, scenario.statuses_to_restore()
        )
        await self._realtime.publish(scenario.user_id, SCENARIO_FINISHED_EVENT, _payload(scenario))
        await self._dispatcher.dispatch(scenario.pull_events())
        await self._notifier.notify(
            scenario.user_id, self._notifications.scenario_failed(str(scenario.id), reason.value)
        )

    async def _report_progress(self, scenario: Scenario, temperature: Temperature | None) -> None:
        """Send one throttled progress message for a running scenario.

        Args:
            scenario: Scenario running through its stages.
            temperature: What the sensors measured, if anything.

        Returns:
            None.
        """
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


def _restorable(captured: dict[DeviceId, DeviceStatus]) -> dict[DeviceId, DeviceStatus]:
    """Keep the captured states a capability can put a device back into.

    Args:
        captured: States the devices were in right before the scenario acted.

    Returns:
        dict[DeviceId, DeviceStatus]: States to restore, fewest necessary.
    """
    return {
        device_id: status
        for device_id, status in captured.items()
        if DeviceStatus.restored_by(status) is not None
    }


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
