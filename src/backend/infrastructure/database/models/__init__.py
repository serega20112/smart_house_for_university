"""Декларативное описание всех таблиц реляционного хранилища."""

from __future__ import annotations

from backend.infrastructure.database.models.accounts import UserModel
from backend.infrastructure.database.models.automation import (
    AutomationModel,
    AutomationParticipantModel,
)
from backend.infrastructure.database.models.base import Base
from backend.infrastructure.database.models.boards import (
    BoardNetworkModel,
    EspClaimModel,
    EspDeviceModel,
)
from backend.infrastructure.database.models.devices import DeviceCapabilityModel, DeviceModel
from backend.infrastructure.database.models.personalization import (
    DashboardModel,
    DashboardWidgetModel,
    PreferencesModel,
)
from backend.infrastructure.database.models.reference_phrases import REFERENCE_PHRASES
from backend.infrastructure.database.models.scenarios import (
    ScenarioActionModel,
    ScenarioCapturedStatusModel,
    ScenarioModel,
)

__all__ = [
    "REFERENCE_PHRASES",
    "AutomationModel",
    "AutomationParticipantModel",
    "Base",
    "BoardNetworkModel",
    "DashboardModel",
    "DashboardWidgetModel",
    "DeviceCapabilityModel",
    "DeviceModel",
    "EspClaimModel",
    "EspDeviceModel",
    "PreferencesModel",
    "ScenarioActionModel",
    "ScenarioCapturedStatusModel",
    "ScenarioModel",
    "UserModel",
]
