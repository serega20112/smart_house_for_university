"""Входные контракты прикладного слоя: команды и запросы.

Каждый контракт живёт в своём файле внутри папки фичи, а здесь они собраны,
чтобы вызывающий назвал одну точку — фичу, а не ворох несвязанных форм.
Модели чтения (то, что экран показывает) живут в `application.dto.views`.
"""

from backend.application.dto.account import AuthenticateCommand, RegisterAccountCommand
from backend.application.dto.automation import AutomationPatch
from backend.application.dto.boards import (
    AnnounceBoardCommand,
    ClaimBoardCommand,
    PairBoardCommand,
    SetNetworkCommand,
)
from backend.application.dto.devices import CreateDeviceCommand, UpdateDeviceCommand
from backend.application.dto.home import SubmitCommand
from backend.application.dto.personalization import DashboardPatch, PreferencesPatch
from backend.application.dto.scenario import ScheduleScenarioCommand

__all__ = [
    "AnnounceBoardCommand",
    "AuthenticateCommand",
    "AutomationPatch",
    "ClaimBoardCommand",
    "CreateDeviceCommand",
    "DashboardPatch",
    "PairBoardCommand",
    "PreferencesPatch",
    "RegisterAccountCommand",
    "ScheduleScenarioCommand",
    "SetNetworkCommand",
    "SubmitCommand",
    "UpdateDeviceCommand",
]
