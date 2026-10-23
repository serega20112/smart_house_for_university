"""A partial change of the interface preferences."""

from __future__ import annotations

from dataclasses import dataclass

from backend.domain.aggregates.preferences.user_preferences import (
    InterfaceLanguage,
    TemperatureUnit,
    Theme,
)


@dataclass(frozen=True, slots=True)
class PreferencesPatch:
    """The fields of the preferences a person wants to change.

    Args:
        temperature_unit: New unit or None.
        theme: New theme or None.
        language: New language or None.
        show_command_chat: New visibility flag or None.

    Returns:
        None.
    """

    temperature_unit: TemperatureUnit | None = None
    theme: Theme | None = None
    language: InterfaceLanguage | None = None
    show_command_chat: bool | None = None
