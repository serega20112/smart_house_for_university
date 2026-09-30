"""Automation settings repository port."""

from __future__ import annotations

from abc import ABC, abstractmethod

from smart_home_backend.domain.entities.automation import AutomationSettings


class AutomationRepository(ABC):
    """Storage of the single automation configuration."""

    @abstractmethod
    async def get(self) -> AutomationSettings:
        """Return the current settings.

        Returns:
            AutomationSettings: Stored settings or defaults when absent.
        """

    @abstractmethod
    async def save(self, settings: AutomationSettings) -> AutomationSettings:
        """Persist the automation settings.

        Args:
            settings: Settings to store.

        Returns:
            AutomationSettings: Stored settings.
        """
