"""Result of one automation cycle."""

from __future__ import annotations

from dataclasses import dataclass, field

from smart_home_backend.application.dto.device.device_execution_result import (
    DeviceExecutionResult,
)
from smart_home_backend.domain.enums.operation import OperationStatus


@dataclass(frozen=True, slots=True)
class AutomationCycleResult:
    """Outcome of a single automation cycle.

    Args:
        status: Result class of the cycle.
        skipped_reason: Machine readable reason why the cycle did nothing.
        demands: Climate demands detected during the cycle.
        actions: Execution results of the performed actions.

    Returns:
        None.
    """

    status: OperationStatus = OperationStatus.SUCCESS
    skipped_reason: str | None = None
    demands: list[str] = field(default_factory=list)
    actions: list[DeviceExecutionResult] = field(default_factory=list)

    @property
    def acted(self) -> bool:
        """Return whether the cycle performed at least one action.

        Returns:
            bool: True when a device was driven.
        """
        return bool(self.actions)
