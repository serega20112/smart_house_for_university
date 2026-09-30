"""SQLAlchemy implementation of the scenario repository port."""

from __future__ import annotations

from collections.abc import Sequence

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from smart_home_backend.application.interface.repositories import ScenarioRepository
from smart_home_backend.domain.entities.scenario import Scenario
from smart_home_backend.domain.enums.scenario import ScenarioStatus
from smart_home_backend.infrastructure.database import mappers
from smart_home_backend.infrastructure.database.models import ScenarioRow

ACTIVE_STATUSES = (ScenarioStatus.PENDING.value, ScenarioStatus.RUNNING.value)


class SqlScenarioRepository(ScenarioRepository):
    """Reads and writes scenarios through an async SQLAlchemy session."""

    def __init__(self, session: AsyncSession) -> None:
        """Initialize the repository.

        Args:
            session: Session owned by the current unit of work.

        Returns:
            None.
        """
        self._session = session

    async def list_all(self) -> Sequence[Scenario]:
        """Return every scenario, newest first.

        Returns:
            Sequence[Scenario]: Stored scenarios.
        """
        result = await self._session.execute(
            select(ScenarioRow).order_by(ScenarioRow.created_at.desc())
        )
        return [mappers.scenario_from_row(row) for row in result.scalars().all()]

    async def list_active(self) -> Sequence[Scenario]:
        """Return pending and running scenarios.

        Returns:
            Sequence[Scenario]: Active scenarios.
        """
        result = await self._session.execute(
            select(ScenarioRow)
            .where(ScenarioRow.status.in_(ACTIVE_STATUSES))
            .order_by(ScenarioRow.start_at)
        )
        return [mappers.scenario_from_row(row) for row in result.scalars().all()]

    async def get(self, scenario_id: int) -> Scenario | None:
        """Return a scenario by id.

        Args:
            scenario_id: Identifier of the scenario.

        Returns:
            Scenario | None: Scenario or None when it does not exist.
        """
        row = await self._session.get(ScenarioRow, scenario_id)
        return mappers.scenario_from_row(row) if row else None

    async def save(self, scenario: Scenario) -> Scenario:
        """Create or update a scenario.

        Args:
            scenario: Scenario to persist.

        Returns:
            Scenario: Persisted scenario including its identifier.
        """
        row = await self._session.get(ScenarioRow, scenario.id) if scenario.id else None
        if row is None:
            row = mappers.scenario_to_row(scenario)
            self._session.add(row)
            await self._session.flush()
            scenario.id = row.id
            return scenario

        row.status = scenario.status.value
        row.start_at = scenario.start_at
        row.duration_minutes = scenario.duration_minutes
        row.target = scenario.target
        row.actions = [action.to_dict() for action in scenario.actions]
        row.completion_behavior = scenario.completion_behavior.value
        row.restore_snapshot = {
            str(device_id): value for device_id, value in scenario.restore_snapshot.items()
        }
        await self._session.flush()
        return scenario

    async def delete(self, scenario_id: int) -> bool:
        """Delete a scenario.

        Args:
            scenario_id: Identifier of the scenario.

        Returns:
            bool: True when a scenario was removed.
        """
        row = await self._session.get(ScenarioRow, scenario_id)
        if row is None:
            return False
        await self._session.delete(row)
        await self._session.flush()
        return True
