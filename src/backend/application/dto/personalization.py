"""Contracts of the personalized projection."""

from __future__ import annotations

from dataclasses import dataclass

from backend.domain.personalization.dashboard_widget import DashboardWidget
from backend.domain.personalization.user_preferences import (
    InterfaceLanguage,
    TemperatureUnit,
    Theme,
)


@dataclass(frozen=True, slots=True)
class PreferencesPatch:
    """Partial change of the interface preferences.

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


@dataclass(frozen=True, slots=True)
class PreferencesView:
    """Interface preferences as the interface needs them.

    Args:
        temperature_unit: Unit climate values are rendered in.
        theme: Visual theme.
        language: Interface language.
        show_command_chat: Whether the command chat is shown on the dashboard.

    Returns:
        None.
    """

    temperature_unit: TemperatureUnit
    theme: Theme
    language: InterfaceLanguage
    show_command_chat: bool


@dataclass(frozen=True, slots=True)
class DashboardPatch:
    """A new dashboard layout.

    Args:
        widgets: Widgets in the order they have to be rendered.

    Returns:
        None.
    """

    widgets: tuple[DashboardWidget, ...]


@dataclass(frozen=True, slots=True)
class DashboardView:
    """The dashboard layout as the interface needs it.

    Args:
        widgets: Widgets in rendering order.

    Returns:
        None.
    """

    widgets: tuple[DashboardWidget, ...]
