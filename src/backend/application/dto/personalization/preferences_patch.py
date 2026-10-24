"""Частичное изменение настроек интерфейса."""

from __future__ import annotations

from dataclasses import dataclass

from backend.domain.aggregates.preferences.user_preferences import (
    InterfaceLanguage,
    TemperatureUnit,
    Theme,
)


@dataclass(frozen=True, slots=True)
class PreferencesPatch:
    """Поля настроек, которые человек хочет изменить.

    Attributes:
        temperature_unit: Новая единица или None.
        theme: Новая тема или None.
        language: Новый язык или None.
        show_command_chat: Новый признак показа или None.
    """

    temperature_unit: TemperatureUnit | None = None
    theme: Theme | None = None
    language: InterfaceLanguage | None = None
    show_command_chat: bool | None = None
