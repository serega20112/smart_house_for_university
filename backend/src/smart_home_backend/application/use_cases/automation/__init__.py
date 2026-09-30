"""Automation use cases."""

from smart_home_backend.application.use_cases.automation.run_automation_cycle import (
    RunAutomationCycleUseCase,
)
from smart_home_backend.application.use_cases.automation.toggle_automation import (
    ToggleAutomationUseCase,
)
from smart_home_backend.application.use_cases.automation.update_automation import (
    UpdateAutomationUseCase,
    automation_payload,
)

__all__ = [
    "RunAutomationCycleUseCase",
    "ToggleAutomationUseCase",
    "UpdateAutomationUseCase",
    "automation_payload",
]
