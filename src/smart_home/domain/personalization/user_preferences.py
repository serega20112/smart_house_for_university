"""Interface preferences of one account.

Preferences are a projection, not a business decision: the very same frontend build
renders a different theme, language and unit for every account. The values are
strict enumerations rather than free text, so an interface can never store a
setting it is unable to draw.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import Self

from smart_home.domain.identifiers import UserId


class TemperatureUnit(StrEnum):
    """Unit climate values are rendered in."""

    CELSIUS = "C"
    FAHRENHEIT = "F"


class Theme(StrEnum):
    """Visual theme of the interface."""

    DARK = "dark"
    LIGHT = "light"


class InterfaceLanguage(StrEnum):
    """Language the interface speaks."""

    RUSSIAN = "ru"
    ENGLISH = "en"


@dataclass(frozen=True, slots=True)
class UserPreferences:
    """The projection settings of one account.

    Args:
        user_id: Owner of the preferences.
        temperature_unit: Unit climate values are rendered in.
        theme: Visual theme.
        language: Interface language.
        show_command_chat: Whether the command chat is shown on the dashboard.

    Returns:
        None.
    """

    user_id: UserId
    temperature_unit: TemperatureUnit = TemperatureUnit.CELSIUS
    theme: Theme = Theme.DARK
    language: InterfaceLanguage = InterfaceLanguage.RUSSIAN
    show_command_chat: bool = True

    def updated(
        self,
        *,
        temperature_unit: TemperatureUnit | None = None,
        theme: Theme | None = None,
        language: InterfaceLanguage | None = None,
        show_command_chat: bool | None = None,
    ) -> Self:
        """Return the preferences with the given fields changed.

        Every field is optional and None means "keep", so a partial update never
        has to rebuild the whole object from an untyped dictionary.

        Args:
            temperature_unit: New unit or None to keep the current one.
            theme: New theme or None to keep the current one.
            language: New language or None to keep the current one.
            show_command_chat: New visibility flag or None to keep the current one.

        Returns:
            Self: Updated preferences.
        """
        return UserPreferences(
            user_id=self.user_id,
            temperature_unit=self.temperature_unit
            if temperature_unit is None
            else temperature_unit,
            theme=self.theme if theme is None else theme,
            language=self.language if language is None else language,
            show_command_chat=(
                self.show_command_chat if show_command_chat is None else show_command_chat
            ),
        )

    @classmethod
    def create(cls, user_id: UserId) -> Self:
        """Build the preferences a fresh account starts with.

        Args:
            user_id: Owner of the preferences.

        Returns:
            Self: Default preferences.
        """
        return cls(user_id=user_id)
