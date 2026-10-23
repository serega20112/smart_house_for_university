"""A deferred action the user asked for."""

from __future__ import annotations

from dataclasses import dataclass

from backend.domain.value_objects.scenario.completion_behavior import CompletionBehavior
from backend.domain.value_objects.scenario.scenario_action import ScenarioAction


@dataclass(frozen=True, slots=True)
class ScheduleScenarioCommand:
    """The values of a scenario the interface is asked to schedule.

    Args:
        action: The single action the scenario performs.
        delay_minutes: How long to wait before acting.
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
