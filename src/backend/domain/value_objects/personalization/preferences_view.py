"""Настройки интерфейса в том виде, в каком их показывают экрану."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from backend.domain.aggregates.preferences.user_preferences import (
        InterfaceLanguage,
        TemperatureUnit,
        Theme,
    )


@dataclass(frozen=True, slots=True)
class PreferencesView:
    """Настройки интерфейса человека для экрана.

    Attributes:
        temperature_unit: Единица, в которой показывают климат.
        theme: Визуальная тема.
        language: Язык интерфейса.
        show_command_chat: Показывать ли чат команд на дашборде.
    """

    temperature_unit: TemperatureUnit
    theme: Theme
    language: InterfaceLanguage
    show_command_chat: bool
