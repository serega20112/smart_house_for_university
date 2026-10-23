"""Декларативное описание всех таблиц реляционного хранилища."""

from __future__ import annotations

from backend.infrastructure.database.tables.accounts import UserRow
from backend.infrastructure.database.tables.automation import (
    AutomationParticipantRow,
    AutomationRow,
)
from backend.infrastructure.database.tables.base import Base
from backend.infrastructure.database.tables.boards import BoardNetworkRow, EspClaimRow, EspDeviceRow
from backend.infrastructure.database.tables.devices import DeviceCapabilityRow, DeviceRow
from backend.infrastructure.database.tables.personalization import (
    DashboardRow,
    DashboardWidgetRow,
    PreferencesRow,
)
from backend.infrastructure.database.tables.reference_phrases import REFERENCE_PHRASES
from backend.infrastructure.database.tables.scenarios import (
    ScenarioActionRow,
    ScenarioCapturedStatusRow,
    ScenarioRow,
)

__all__ = [
    "REFERENCE_PHRASES",
    "AutomationParticipantRow",
    "AutomationRow",
    "Base",
    "BoardNetworkRow",
    "DashboardRow",
    "DashboardWidgetRow",
    "DeviceCapabilityRow",
    "DeviceRow",
    "EspClaimRow",
    "EspDeviceRow",
    "PreferencesRow",
    "ScenarioActionRow",
    "ScenarioCapturedStatusRow",
    "ScenarioRow",
    "UserRow",
]
