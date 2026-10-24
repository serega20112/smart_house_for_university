"""Частичное изменение настроек интерфейса."""

from __future__ import annotations

from dataclasses import dataclass

from backend.domain.value_objects.personalization.interface_language import InterfaceLanguage
from backend.domain.value_objects.personalization.temperature_unit import TemperatureUnit
from backend.domain.value_objects.personalization.theme import Theme


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
