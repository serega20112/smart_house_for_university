"""Application data transfer objects.

Commands and queries describe the inputs of use cases and are grouped by
feature. Outputs of use cases are domain objects, cross service results such as
execution reports live here as well, and transport payloads are produced by the
presentation layer.
"""

from smart_home_backend.application.dto.automation import (
    AutomationCycleResult,
    UpdateAutomationCommand,
)
from smart_home_backend.application.dto.command import CommandResult, ProcessUserCommand
from smart_home_backend.application.dto.device import (
    CreateDeviceCommand,
    DeviceExecutionResult,
    UpdateDeviceCommand,
)
from smart_home_backend.application.dto.scenario import CreateScenarioCommand

__all__ = [
    "AutomationCycleResult",
    "CommandResult",
    "CreateDeviceCommand",
    "CreateScenarioCommand",
    "DeviceExecutionResult",
    "ProcessUserCommand",
    "UpdateAutomationCommand",
    "UpdateDeviceCommand",
]
