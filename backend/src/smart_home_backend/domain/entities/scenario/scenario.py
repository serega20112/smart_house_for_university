"""Timed scenario entity."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta

from smart_home_backend.domain.entities.scenario.scenario_action import ScenarioAction
from smart_home_backend.domain.enums.scenario import CompletionBehavior, ScenarioStatus


@dataclass
class Scenario:
    """Timed scenario such as "cool the room to 20 degrees in half an hour".

    Args:
        id: Persistence identifier, zero for a not yet stored scenario.
        status: Current lifecycle stage.
        created_at: Creation timestamp.
        start_at: Moment the scenario starts acting.
        actions: Actions performed once the scenario starts.
        target: Optional target description taken from the user command.
        duration_minutes: Optional duration limit in minutes.
        completion_behavior: What happens with devices after completion.
        restore_snapshot: Device statuses captured before the start, used by
            the RESTORE_PREVIOUS_STATE behavior.

    Returns:
        None.
    """

    id: int
    status: ScenarioStatus
    created_at: datetime
    start_at: datetime
    actions: list[ScenarioAction] = field(default_factory=list)
    target: str | None = None
    duration_minutes: int | None = None
    completion_behavior: CompletionBehavior = CompletionBehavior.CONTINUE_AUTOMATION

    restore_snapshot: dict[int, str] = field(default_factory=dict)

    @property
    def is_active(self) -> bool:
        """Return whether the scenario still occupies the control priority.

        Returns:
            bool: True for pending and running scenarios.
        """
        return self.status in (ScenarioStatus.PENDING, ScenarioStatus.RUNNING)

    def should_start(self, now: datetime) -> bool:
        """Return whether the scenario start moment has come.

        Args:
            now: Current moment.

        Returns:
            bool: True when the scenario must start.
        """
        return self.status is ScenarioStatus.PENDING and now >= self.start_at

    def ends_at(self) -> datetime | None:
        """Return the moment the scenario duration expires.

        Returns:
            datetime | None: End moment or None when the scenario is unbounded.
        """
        if self.duration_minutes is None:
            return None
        return self.start_at + timedelta(minutes=self.duration_minutes)

    def is_expired(self, now: datetime) -> bool:
        """Return whether the scenario duration has elapsed.

        Args:
            now: Current moment.

        Returns:
            bool: True when the scenario ran out of time.
        """
        end = self.ends_at()
        return end is not None and now >= end
