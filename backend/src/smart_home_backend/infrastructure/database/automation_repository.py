"""SQLAlchemy implementation of the automation repository port."""

from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from smart_home_backend.application.interface.repositories import AutomationRepository
from smart_home_backend.domain.entities.automation import AutomationSettings
from smart_home_backend.infrastructure.database import mappers
from smart_home_backend.infrastructure.database.models import (
    AUTOMATION_SINGLETON_ID,
    AutomationRow,
)


class SqlAutomationRepository(AutomationRepository):
    """Reads and writes the single automation configuration row."""

    def __init__(self, session: AsyncSession) -> None:
        """Initialize the repository.

        Args:
            session: Session owned by the current unit of work.

        Returns:
            None.
        """
        self._session = session

    async def get(self) -> AutomationSettings:
        """Return the current settings, creating defaults on first access.

        Returns:
            AutomationSettings: Stored settings or defaults.
        """
        row = await self._session.get(AutomationRow, AUTOMATION_SINGLETON_ID)
        if row is None:
            return await self.save(AutomationSettings())
        return mappers.automation_from_row(row)

    async def save(self, settings: AutomationSettings) -> AutomationSettings:
        """Persist the automation settings.

        Args:
            settings: Settings to store.

        Returns:
            AutomationSettings: Stored settings.
        """
        row = await self._session.get(AutomationRow, AUTOMATION_SINGLETON_ID)
        if row is None:
            self._session.add(mappers.automation_to_row(settings))
        else:
            row.enabled = settings.enabled
            row.target_temperature = settings.target_temperature
            row.temperature_tolerance = settings.temperature_tolerance
            row.target_humidity = settings.target_humidity
            row.humidity_tolerance = settings.humidity_tolerance
            row.participating_device_ids = sorted(settings.participating_device_ids)
        await self._session.flush()
        return settings
