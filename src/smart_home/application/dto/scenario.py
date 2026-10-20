"""Contracts of the scenario operations."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from smart_home.domain.identifiers import ScenarioId
from smart_home.domain.scenarios.completion_behavior import CompletionBehavior
from smart_home.domain.scenarios.scenario_action import ScenarioAction
from smart_home.domain.scenarios.scenario_status import ScenarioStatus


@dataclass(frozen=True, slots=True)
class ScheduleScenarioCommand:
    """A deferred action the user asked for.

    Args:
        delay_minutes: How long to wait before acting.
        action: The single action the scenario performs.
        target: Area or object the user named.
        completion_behavior: What happens with the devices afterwards.
        duration_minutes: How long the scenario may run.

    Returns:
        None.
    """

    action: ScenarioAction
    delay_minutes: int | None = None
    target: str | None = None
    completion_behavior: CompletionBehavior = CompletionBehavior.LEAVE_TO_AUTOMATION
    duration_minutes: int | None = None


@dataclass(frozen=True, slots=True)
class ScenarioView:
    """One scenario as the interface needs it.

    Args:
        id: Identifier of the scenario.
        status: Stage the scenario is in.
        created_at: Moment the scenario was stored.
        start_at: Moment the scenario starts acting.
        duration_minutes: How long it may run, or None when it is unbounded.
        target: Area or object the user named.
        completion_behavior: What happens with the devices afterwards.
        actions: Actions the scenario performs.

    Returns:
        None.
    """

    id: ScenarioId
    status: ScenarioStatus
    created_at: datetime
    start_at: datetime
    duration_minutes: int | None
    target: str | None
    completion_behavior: CompletionBehavior
    actions: tuple[ScenarioAction, ...]
