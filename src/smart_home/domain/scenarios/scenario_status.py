"""Lifecycle stage of a timed scenario."""

from __future__ import annotations

from enum import StrEnum


class ScenarioStatus(StrEnum):
    """Where a scenario is in its life.

    Args:
        None.

    Returns:
        None.
    """

    PENDING = "PENDING"
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"

    @property
    def is_final(self) -> bool:
        """Return whether the scenario will never act again.

        Returns:
            bool: True for completed, failed and cancelled scenarios.
        """
        return self in _FINAL_STATUSES

    @property
    def holds_control_priority(self) -> bool:
        """Return whether the scenario still outranks automation.

        Returns:
            bool: True for pending and running scenarios.
        """
        return self in (ScenarioStatus.PENDING, ScenarioStatus.RUNNING)


_FINAL_STATUSES: frozenset[ScenarioStatus] = frozenset(
    {
        ScenarioStatus.COMPLETED,
        ScenarioStatus.FAILED,
        ScenarioStatus.CANCELLED,
    }
)
