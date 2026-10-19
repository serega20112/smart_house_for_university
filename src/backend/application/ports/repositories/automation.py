"""Automation repository port."""

from __future__ import annotations

from typing import Protocol

from backend.domain.climate.automation_settings import AutomationSettings
from backend.domain.identifiers import UserId


class AutomationRepository(Protocol):
    """Storage of the automation configuration of one account.

    Reading returns None for an account that never configured automation instead of
    quietly inserting a default row, which is what keeps a select from turning
    into a write behind the caller's back.
    """

    async def get(self, user_id: UserId) -> AutomationSettings | None:
        """Return the stored configuration.

        Args:
            user_id: Owner of the configuration.

        Returns:
            AutomationSettings | None: Stored configuration, or None when the
            account never configured automation.
        """

    async def save(self, settings: AutomationSettings) -> None:
        """Store the automation configuration of an account.

        Args:
            settings: Configuration to persist.

        Returns:
            None.
        """
