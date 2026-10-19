"""Dashboard and preferences repository ports."""

from __future__ import annotations

from typing import Protocol

from backend.domain.identifiers import UserId
from backend.domain.personalization.dashboard_state import DashboardState
from backend.domain.personalization.user_preferences import UserPreferences


class DashboardRepository(Protocol):
    """Storage of the dashboard layout of one account."""

    async def get(self, user_id: UserId) -> DashboardState | None:
        """Return the stored layout.

        Args:
            user_id: Owner of the layout.

        Returns:
            DashboardState | None: Stored layout, or None when the account never
            customized it.
        """

    async def save(self, dashboard: DashboardState) -> None:
        """Store the layout of an account.

        Args:
            dashboard: Layout to persist.

        Returns:
            None.
        """


class PreferencesRepository(Protocol):
    """Storage of the interface preferences of one account."""

    async def get(self, user_id: UserId) -> UserPreferences | None:
        """Return the stored preferences.

        Args:
            user_id: Owner of the preferences.

        Returns:
            UserPreferences | None: Stored preferences, or None when the account
            never changed them.
        """

    async def save(self, preferences: UserPreferences) -> None:
        """Store the preferences of an account.

        Args:
            preferences: Preferences to persist.

        Returns:
            None.
        """
