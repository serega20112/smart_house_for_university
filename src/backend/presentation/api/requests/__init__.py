"""Тела запросов HTTP API и перевод их в команды прикладного слоя.

Маршруты не должны знать, как из полей формы собирается команда: здесь это
делает одна функция на команду, и там же стоят границы, которые интерфейс
проверяет раньше домена.
"""

from backend.presentation.api.requests.auth import (
    LoginBody,
    RegisterBody,
    authenticate_command,
    register_command,
)
from backend.presentation.api.requests.automation import (
    AutomationUpdateBody,
    patch_of,
)
from backend.presentation.api.requests.boards import (
    BoardNetworkBody,
    ClaimBoardBody,
    PairBoardBody,
    claim_command,
    network_command,
    pair_command,
)
from backend.presentation.api.requests.commands import CommandBody
from backend.presentation.api.requests.devices import (
    DeviceCreateBody,
    DeviceUpdateBody,
    create_command,
    update_command,
)
from backend.presentation.api.requests.personalization import (
    DashboardBody,
    PreferencesBody,
    dashboard_patch,
    preferences_patch,
)
from backend.presentation.api.requests.scenarios import ScenarioCreateBody, schedule_command

__all__ = [
    "AutomationUpdateBody",
    "BoardNetworkBody",
    "ClaimBoardBody",
    "CommandBody",
    "DashboardBody",
    "DeviceCreateBody",
    "DeviceUpdateBody",
    "LoginBody",
    "PairBoardBody",
    "PreferencesBody",
    "RegisterBody",
    "ScenarioCreateBody",
    "authenticate_command",
    "claim_command",
    "create_command",
    "dashboard_patch",
    "network_command",
    "pair_command",
    "patch_of",
    "preferences_patch",
    "register_command",
    "schedule_command",
    "update_command",
]
