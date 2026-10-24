"""Мапперы настроек интерфейса."""

from __future__ import annotations

from backend.domain.entities.personalization.user_preferences import UserPreferences
from backend.domain.identifiers import UserId
from backend.domain.value_objects.personalization.interface_language import InterfaceLanguage
from backend.domain.value_objects.personalization.temperature_unit import TemperatureUnit
from backend.domain.value_objects.personalization.theme import Theme
from backend.infrastructure.database.models import (
    PreferencesModel,
)


def preferences_to_row(preferences: UserPreferences) -> PreferencesModel:
    """Строит строку, описывающую настройки интерфейса аккаунта."""
    return PreferencesModel(
        user_id=preferences.user_id.value,
        temperature_unit=preferences.temperature_unit.value,
        theme=preferences.theme.value,
        language=preferences.language.value,
        show_command_chat=preferences.show_command_chat,
    )


def preferences_from_row(row: PreferencesModel) -> UserPreferences:
    """Строит настройки, описанные строкой."""
    return UserPreferences(
        user_id=UserId.parse(row.user_id),
        temperature_unit=TemperatureUnit(row.temperature_unit),
        theme=Theme(row.theme),
        language=InterfaceLanguage(row.language),
        show_command_chat=row.show_command_chat,
    )
