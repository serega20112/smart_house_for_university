"""Application use cases.

Every user facing action lives in its own module, grouped by feature, and exposes
a single ``execute`` method. Use cases depend on ports only, so the same action
can be triggered from any interface.
"""

from smart_home_backend.application.use_cases.automation import (
    RunAutomationCycleUseCase,
    ToggleAutomationUseCase,
    UpdateAutomationUseCase,
)
from smart_home_backend.application.use_cases.climate import (
    RunClimateCapabilityUseCase,
    SetTargetHumidityUseCase,
    SetTargetTemperatureUseCase,
)
from smart_home_backend.application.use_cases.command import ProcessUserCommandUseCase
from smart_home_backend.application.use_cases.device import (
    SetDeviceModeUseCase,
    TurnAllDevicesUseCase,
    TurnDeviceOffUseCase,
    TurnDeviceOnUseCase,
)
from smart_home_backend.application.use_cases.device_config import (
    CreateDeviceUseCase,
    DeleteDeviceUseCase,
    UpdateDeviceUseCase,
)
from smart_home_backend.application.use_cases.query import (
    GetActiveScenariosUseCase,
    GetAutomationSettingsUseCase,
    GetDeviceUseCase,
    GetDevicesUseCase,
    GetHomeSnapshotUseCase,
    HomeSnapshot,
)
from smart_home_backend.application.use_cases.scenario import (
    CancelScenarioUseCase,
    CreateScenarioUseCase,
    TickScenariosUseCase,
)

__all__ = [
    "CancelScenarioUseCase",
    "CreateDeviceUseCase",
    "CreateScenarioUseCase",
    "DeleteDeviceUseCase",
    "GetActiveScenariosUseCase",
    "GetAutomationSettingsUseCase",
    "GetDeviceUseCase",
    "GetDevicesUseCase",
    "GetHomeSnapshotUseCase",
    "HomeSnapshot",
    "ProcessUserCommandUseCase",
    "RunAutomationCycleUseCase",
    "RunClimateCapabilityUseCase",
    "SetDeviceModeUseCase",
    "SetTargetHumidityUseCase",
    "SetTargetTemperatureUseCase",
    "TickScenariosUseCase",
    "ToggleAutomationUseCase",
    "TurnAllDevicesUseCase",
    "TurnDeviceOffUseCase",
    "TurnDeviceOnUseCase",
    "UpdateAutomationUseCase",
    "UpdateDeviceUseCase",
]
