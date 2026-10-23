"""Timed scenario aggregate.

A scenario is a deferred promise: "make it twenty degrees in half an hour". The
aggregate owns that promise. It knows when it has to start, when its goal counts
as reached, when it ran out of time and what has to happen with the devices
afterwards, and it refuses every transition that does not make sense.

Nothing outside the aggregate changes its status, its snapshot or its actions, so
the rules cannot be bypassed by a caller that simply assigns a field.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Self

from backend.domain.events import ScenarioFinished, ScenarioScheduled, ScenarioStarted
from backend.domain.exceptions import (
    IllegalScenarioTransitionError,
    ScenarioAlreadyFinishedError,
)
from backend.domain.identifiers import DeviceId, ScenarioId, UserId
from backend.domain.value_objects.climate.climate_reading import ClimateReading
from backend.domain.value_objects.climate.temperature import Temperature
from backend.domain.value_objects.devices.device_status import DeviceStatus
from backend.domain.value_objects.scenario.completion_behavior import CompletionBehavior
from backend.domain.value_objects.scenario.scenario_action import ScenarioAction
from backend.domain.value_objects.scenario.scenario_status import ScenarioStatus

GOAL_TOLERANCE_C = 0.5
MAX_TARGET_LENGTH = 120


@dataclass
class Scenario:
    """A promise about the climate of one home at a later moment.

    Args:
        id: Identifier assigned at creation.
        user_id: Owner of the scenario, part of the aggregate so that no method
            has to be told whose home it is acting on.
        status: Stage the scenario is in.
        created_at: Moment the scenario was stored.
        start_at: Moment the scenario starts acting.
        duration_minutes: How long it may run, or None when it is unbounded.
        target: Area or object the user named, or None.
        completion_behavior: What happens with the devices afterwards.
        actions: Actions performed once the scenario starts.
        captured_statuses: Device states captured before the start, used by the
            restore behaviour.
        _events: Facts recorded since the scenario was loaded.

    Returns:
        None.
    """

    id: ScenarioId
    user_id: UserId
    status: ScenarioStatus
    created_at: datetime
    start_at: datetime
    duration_minutes: int | None = None
    target: str | None = None
    completion_behavior: CompletionBehavior = CompletionBehavior.LEAVE_TO_AUTOMATION
    actions: tuple[ScenarioAction, ...] = ()
    captured_statuses: dict[DeviceId, DeviceStatus] = field(default_factory=dict)
    version: int = 0
    _events: list[ScenarioScheduled | ScenarioStarted | ScenarioFinished] = field(
        default_factory=list, repr=False, compare=False
    )

    @property
    def holds_control_priority(self) -> bool:
        """Return whether the scenario still outranks automation.

        Returns:
            bool: True while the scenario is pending or running.
        """
        return self.status.holds_control_priority

    @property
    def ends_at(self) -> datetime | None:
        """Return the moment the scenario runs out of time.

        Returns:
            datetime | None: End moment, or None when the scenario is unbounded.
        """
        if self.duration_minutes is None:
            return None
        return self.start_at + timedelta(minutes=self.duration_minutes)

    def is_due(self, now: datetime) -> bool:
        """Return whether the start moment has come.

        Args:
            now: Moment to judge at.

        Returns:
            bool: True when the scenario has to start acting.
        """
        return self.status is ScenarioStatus.PENDING and now >= self.start_at

    def has_timed_out(self, now: datetime) -> bool:
        """Return whether the scenario ran out of time.

        Args:
            now: Moment to judge at.

        Returns:
            bool: True when the duration has elapsed.
        """
        end = self.ends_at
        return end is not None and now >= end

    def is_goal_reached(self, reading: ClimateReading) -> bool:
        """Return whether every requested target temperature was reached.

        Args:
            reading: Current sensor reading.

        Returns:
            bool: True when nothing has to be waited for any more.
        """
        measured = reading.temperature
        if measured is None:
            return False
        return all(
            action.target_temperature is None
            or measured.distance_to(action.target_temperature) <= GOAL_TOLERANCE_C
            for action in self.actions
        )

    def start(self, current_statuses: dict[DeviceId, DeviceStatus]) -> ScenarioStarted:
        """Begin acting on the home.

        The states the devices had a moment before are captured here rather than
        by the caller, because the restore behaviour depends on them and the
        aggregate is what knows whether it will need them.

        Args:
            current_statuses: State of every device right before the start.

        Returns:
            ScenarioStarted: The recorded fact.

        Raises:
            IllegalScenarioTransitionError: When the scenario is not pending.
        """
        self._require_transition(ScenarioStatus.PENDING, ScenarioStatus.RUNNING)
        self.captured_statuses = dict(current_statuses)
        self.status = ScenarioStatus.RUNNING
        event = ScenarioStarted(user_id=self.user_id, scenario_id=self.id)
        self._events.append(event)
        return event

    def complete(self, reason: str) -> ScenarioFinished:
        """Finish successfully.

        Args:
            reason: Why the scenario finished.

        Returns:
            ScenarioFinished: The recorded fact.

        Raises:
            IllegalScenarioTransitionError: When the scenario never started.
        """
        self._require_transition(ScenarioStatus.RUNNING, ScenarioStatus.COMPLETED)
        return self._finish(ScenarioStatus.COMPLETED, reason)

    def cancel(self) -> ScenarioFinished:
        """Give the scenario up before it finished.

        Cancelling a running scenario is allowed and normal: a person changed
        their mind. What the aggregate refuses is cancelling twice.

        Returns:
            ScenarioFinished: The recorded fact.

        Raises:
            ScenarioAlreadyFinishedError: When the scenario already finished.
        """
        if self.status.is_final:
            raise ScenarioAlreadyFinishedError(str(self.id), self.status.value)
        return self._finish(ScenarioStatus.CANCELLED, "cancelled_by_user")

    def fail(self, reason: str) -> ScenarioFinished:
        """Record that the scenario could not be carried out.

        Args:
            reason: Why it failed.

        Returns:
            ScenarioFinished: The recorded fact.

        Raises:
            IllegalScenarioTransitionError: When the scenario already finished.
        """
        if self.status.is_final:
            raise ScenarioAlreadyFinishedError(str(self.id), self.status.value)
        return self._finish(ScenarioStatus.FAILED, reason)

    def statuses_to_restore(self) -> dict[DeviceId, DeviceStatus]:
        """Return the states the devices have to be put back into.

        Returns:
            dict[DeviceId, DeviceStatus]: States to restore, empty when the
            devices are to be left to automation.
        """
        restored: dict[DeviceId, DeviceStatus] = {}
        for device_id, captured in self.captured_statuses.items():
            target = self.completion_behavior.status_to_apply(captured)
            if target is not None:
                restored[device_id] = target
        if self.completion_behavior is CompletionBehavior.SWITCH_EVERYTHING_OFF:
            return dict.fromkeys(self.captured_statuses, DeviceStatus.OFF)
        return restored

    def pull_events(self) -> tuple[ScenarioScheduled | ScenarioStarted | ScenarioFinished, ...]:
        """Return the recorded facts and forget them.

        Returns:
            tuple[ScenarioScheduled | ScenarioStarted | ScenarioFinished, ...]:
            Facts recorded since the last call.
        """
        recorded = tuple(self._events)
        self._events.clear()
        return recorded

    def _finish(self, status: ScenarioStatus, reason: str) -> ScenarioFinished:
        self.status = status
        event = ScenarioFinished(
            user_id=self.user_id,
            scenario_id=self.id,
            status=status.value,
            reason=reason,
        )
        self._events.append(event)
        return event

    def _require_transition(self, current: ScenarioStatus, requested: ScenarioStatus) -> None:
        if self.status is not current:
            raise IllegalScenarioTransitionError(str(self.id), self.status.value, requested.value)

    @classmethod
    def schedule(
        cls,
        user_id: UserId,
        created_at: datetime,
        delay_minutes: int | None = None,
        actions: tuple[ScenarioAction, ...] = (),
        target: str | None = None,
        completion_behavior: CompletionBehavior = CompletionBehavior.LEAVE_TO_AUTOMATION,
        duration_minutes: int | None = None,
    ) -> Self:
        """Build a scenario waiting for its start moment.

        Args:
            user_id: Owner of the scenario.
            created_at: Moment the scenario was asked for.
            delay_minutes: How long to wait before acting.
            actions: Actions to perform once started.
            target: Area or object the user named.
            completion_behavior: What happens with the devices afterwards.
            duration_minutes: How long the scenario may run.

        Returns:
            Self: Created scenario.

        Raises:
            ValueError: When the named target is longer than the model allows.
        """
        if target is not None and len(target.strip()) > MAX_TARGET_LENGTH:
            raise ValueError(f"scenario target is longer than {MAX_TARGET_LENGTH} characters")
        delay = delay_minutes if delay_minutes and delay_minutes > 0 else 0
        scenario = cls(
            id=ScenarioId.generate(),
            user_id=user_id,
            status=ScenarioStatus.PENDING,
            created_at=created_at,
            start_at=created_at + timedelta(minutes=delay),
            duration_minutes=duration_minutes,
            target=None if target is None else target.strip() or None,
            completion_behavior=completion_behavior,
            actions=actions,
        )
        scenario._events.append(ScenarioScheduled(user_id=user_id, scenario_id=scenario.id))
        return scenario

    @classmethod
    def action_for(
        cls, capability: object, target_temperature: Temperature | None = None
    ) -> ScenarioAction:
        """Build the single action of a simple scenario.

        Args:
            capability: Capability the scenario asks for.
            target_temperature: Temperature the action aims for.

        Returns:
            ScenarioAction: Action to put into a scenario.
        """
        return ScenarioAction(capability=capability, target_temperature=target_temperature)
