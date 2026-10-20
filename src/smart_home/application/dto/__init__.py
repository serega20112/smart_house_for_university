"""Contracts exchanged between the application layer and the interface.

The DTOs of the application are the only shape the interface sees. The enums and
the identifiers of the domain are re-exported here, because the interface has to
name them in a request body or in a response, and the rule of the architecture is
that presentation never imports the domain directly.
"""

from smart_home.application.dto.account import (
    AccountProfile,
    AuthenticateCommand,
    AuthenticatedSession,
    RegisterAccountCommand,
)
from smart_home.application.dto.automation import AutomationPatch, AutomationView
from smart_home.application.dto.device import (
    CapabilityReport,
    CreateDeviceCommand,
    DeviceView,
    UpdateDeviceCommand,
)
from smart_home.application.dto.esp import (
    AnnounceBoardCommand,
    BoardClaimView,
    BoardNetworkView,
    BoardView,
    ClaimBoardCommand,
    PairBoardCommand,
    PairedBoard,
    SetNetworkCommand,
)
from smart_home.application.dto.home import CommandReply, HomeSnapshotView, ReadingView
from smart_home.application.dto.scenario import ScenarioView, ScheduleScenarioCommand
from smart_home.application.dto.version import ApplicationVersion
from smart_home.domain.climate.humidity import Humidity
from smart_home.domain.climate.temperature import Temperature
from smart_home.domain.devices.capability import Capability
from smart_home.domain.devices.device_kind import DeviceKind
from smart_home.domain.devices.device_status import DeviceStatus
from smart_home.domain.identifiers import DeviceId, EspDeviceId, ScenarioId, UserId
from smart_home.domain.scenarios.completion_behavior import CompletionBehavior
from smart_home.domain.scenarios.scenario_action import ScenarioAction
from smart_home.domain.scenarios.scenario_status import ScenarioStatus

__all__ = [
    "AccountProfile",
    "AnnounceBoardCommand",
    "ApplicationVersion",
    "AuthenticateCommand",
    "AuthenticatedSession",
    "AutomationPatch",
    "AutomationView",
    "BoardClaimView",
    "BoardNetworkView",
    "BoardView",
    "Capability",
    "CapabilityReport",
    "ClaimBoardCommand",
    "CommandReply",
    "CompletionBehavior",
    "CreateDeviceCommand",
    "DeviceId",
    "DeviceKind",
    "DeviceStatus",
    "DeviceView",
    "EspDeviceId",
    "HomeSnapshotView",
    "Humidity",
    "PairBoardCommand",
    "PairedBoard",
    "ReadingView",
    "RegisterAccountCommand",
    "ScenarioAction",
    "ScenarioId",
    "ScenarioStatus",
    "ScenarioView",
    "ScheduleScenarioCommand",
    "SetNetworkCommand",
    "Temperature",
    "UpdateDeviceCommand",
    "UserId",
]
