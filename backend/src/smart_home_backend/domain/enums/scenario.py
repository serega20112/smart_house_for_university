"""Scenario status and completion behavior enumerations."""

from __future__ import annotations

from smart_home_backend.domain.enums.base import StrEnum


class ScenarioStatus(StrEnum):
    """Lifecycle stage of a timed scenario."""

    PENDING = "PENDING"
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"


class CompletionBehavior(StrEnum):
    """What happens with the devices once a scenario is finished."""

    OFF = "OFF"
    RESTORE_PREVIOUS_STATE = "RESTORE_PREVIOUS_STATE"
    CONTINUE_AUTOMATION = "CONTINUE_AUTOMATION"
