"""Command that schedules a timed scenario."""

from __future__ import annotations

from dataclasses import dataclass

from smart_home_backend.domain.enums.device import Capability
from smart_home_backend.domain.enums.scenario import CompletionBehavior


@dataclass(frozen=True, slots=True)
class CreateScenarioCommand:
    """Input of the scenario creation use case.

    Args:
        delay_minutes: Delay before the scenario starts acting.
        target_temperature: Target temperature of the scenario action.
        capability: Capability the scenario performs.
        completion_behavior: What happens with devices after completion.
        target: Target area or object taken from the user command.

    Returns:
        None.
    """

    delay_minutes: int | None = None
    target_temperature: float | None = None
    capability: Capability | None = None
    completion_behavior: CompletionBehavior = CompletionBehavior.CONTINUE_AUTOMATION
    target: str | None = None
