"""Мапперы настроек интерфейса."""

from __future__ import annotations

from backend.domain.aggregates.preferences.user_preferences import (
    InterfaceLanguage,
    TemperatureUnit,
    Theme,
    UserPreferences,
)
from backend.domain.identifiers import UserId
from backend.infrastructure.database.tables import (
    PreferencesRow,
)


def preferences_to_row(preferences: UserPreferences) -> PreferencesRow:
    """Build the row describing the interface preferences of an account.

    Args:
        preferences: Preferences to serialize.

    Returns:
        PreferencesRow: New row describing the preferences.
    """
    return PreferencesRow(
        user_id=preferences.user_id.value,
        temperature_unit=preferences.temperature_unit.value,
        theme=preferences.theme.value,
        language=preferences.language.value,
        show_command_chat=preferences.show_command_chat,
    )


def preferences_from_row(row: PreferencesRow) -> UserPreferences:
    """Build the preferences a row describes.

    Args:
        row: Row to deserialize.

    Returns:
        UserPreferences: Restored preferences.
    """
    return UserPreferences(
        user_id=UserId.parse(row.user_id),
        temperature_unit=TemperatureUnit(row.temperature_unit),
        theme=Theme(row.theme),
        language=InterfaceLanguage(row.language),
        show_command_chat=row.show_command_chat,
    )
