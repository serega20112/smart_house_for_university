"""Чтения настройки автоматизации.

Чтения стороны выбора: каждое — один вопрос и один читаемый образ.
"""

from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncEngine

from backend.domain.aggregates.automation.automation_settings import AutomationSettings
from backend.domain.identifiers import (
    DeviceId,
    UserId,
)
from backend.domain.value_objects.automation.automation_view import AutomationView
from backend.infrastructure.database import mappers
from backend.infrastructure.database.repositories.base import first_row
from backend.infrastructure.database.repositories.child_rows import (
    participants_of,
)
from backend.infrastructure.database.tables import (
    AutomationRow,
)


class SqlAutomationQueries:
    """Reads of the automation configuration, answered without a transaction.

    Args:
        engine: Engine the reads are executed on.

    Returns:
        None.
    """

    def __init__(self, engine: AsyncEngine) -> None:
        """Initialize the queries.

        Args:
            engine: Engine to read from.

        Returns:
            None.
        """
        self._engine = engine

    async def get(self, user_id: UserId) -> AutomationView:
        """Return the automation configuration of an account.

        An account that never configured automation still gets an answer: the
        defaults are taken from the aggregate itself, so the read model can never
        drift away from the values a fresh home is actually built with.

        Args:
            user_id: Owner of the configuration.

        Returns:
            AutomationView: Configuration shaped for display.
        """
        async with self._engine.connect() as connection:
            row = await first_row(connection, AutomationRow, AutomationRow.user_id == user_id.value)
            participants = await participants_of(connection, user_id)
        if row is None:
            return automation_view_of(AutomationSettings.create(user_id), frozenset())
        return automation_view_of(mappers.automation_from_row(row, participants), participants)


def automation_view_of(
    settings: AutomationSettings, participants: frozenset[DeviceId]
) -> AutomationView:
    """Return the read model of one automation configuration.

    Args:
        settings: Configuration to shape.
        participants: Devices automation is allowed to drive.

    Returns:
        AutomationView: Configuration shaped for display.
    """
    return AutomationView(
        enabled=settings.enabled,
        target_temperature=settings.target_temperature.celsius,
        target_humidity=settings.target_humidity.percent,
        temperature_tolerance=settings.temperature_tolerance,
        humidity_tolerance=settings.humidity_tolerance,
        participating_device_ids=participants,
    )
