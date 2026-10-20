"""Read side of the automation configuration."""

from __future__ import annotations

from typing import Protocol

from smart_home.application.dto.automation import AutomationView
from smart_home.domain.identifiers import UserId


class AutomationQueries(Protocol):
    """Reads of the automation configuration."""

    async def get(self, user_id: UserId) -> AutomationView:
        """Return the automation configuration of an account.

        An account that never configured automation still gets an answer: the
        defaults are part of the read model, not something the reader has to
        invent.

        Args:
            user_id: Owner of the configuration.

        Returns:
            AutomationView: Configuration shaped for display.
        """
