"""Модели ответов HTTP API и перевод образов прикладного слоя в тела ответов."""

from backend.presentation.api.responses.auth import (
    SessionResponse,
    UserResponse,
    profile_of,
    session_of,
)
from backend.presentation.api.responses.automation import AutomationResponse, automation_of
from backend.presentation.api.responses.boards import (
    BoardClaimResponse,
    BoardNetworkResponse,
    BoardPairedResponse,
    BoardResponse,
    board_of,
    claim_of,
    network_of,
    paired_of,
)
from backend.presentation.api.responses.commands import CommandResponse, command_of
from backend.presentation.api.responses.common import (
    HealthResponse,
    OperationResponse,
    StrictModel,
)
from backend.presentation.api.responses.devices import DeviceResponse, device_of
from backend.presentation.api.responses.home import (
    HomeStateResponse,
    ReadingResponse,
    snapshot_of,
)
from backend.presentation.api.responses.personalization import (
    DashboardResponse,
    DashboardWidgetResponse,
    PreferencesResponse,
    dashboard_of,
    preferences_of,
)
from backend.presentation.api.responses.scenarios import (
    ScenarioActionResponse,
    ScenarioResponse,
    scenario_of,
)

__all__ = [
    "AutomationResponse",
    "BoardClaimResponse",
    "BoardNetworkResponse",
    "BoardPairedResponse",
    "BoardResponse",
    "CommandResponse",
    "DashboardResponse",
    "DashboardWidgetResponse",
    "DeviceResponse",
    "HealthResponse",
    "HomeStateResponse",
    "OperationResponse",
    "PreferencesResponse",
    "ReadingResponse",
    "ScenarioActionResponse",
    "ScenarioResponse",
    "SessionResponse",
    "StrictModel",
    "UserResponse",
    "automation_of",
    "board_of",
    "claim_of",
    "command_of",
    "dashboard_of",
    "device_of",
    "network_of",
    "paired_of",
    "preferences_of",
    "profile_of",
    "scenario_of",
    "session_of",
    "snapshot_of",
]
