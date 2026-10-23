"""Хранилище временных сценариев PostgreSQL."""

from __future__ import annotations

from collections.abc import Sequence

from sqlalchemy import delete, insert, select, update
from sqlalchemy.ext.asyncio import AsyncConnection, AsyncSession

from backend.application.errors import (
    ConcurrentModificationError,
)
from backend.domain.aggregates.scenario.scenario import Scenario
from backend.domain.identifiers import (
    DeviceId,
    ScenarioId,
    UserId,
)
from backend.domain.value_objects.devices.device_status import DeviceStatus
from backend.domain.value_objects.scenario.scenario_action import ScenarioAction
from backend.domain.value_objects.scenario.scenario_status import ScenarioStatus
from backend.infrastructure.database import mappers
from backend.infrastructure.database.repositories.base import every_row, first_row, insert_rows
from backend.infrastructure.database.tables import (
    ScenarioActionRow,
    ScenarioCapturedStatusRow,
    ScenarioRow,
)

UNIQUE_VIOLATION = "23505"
Runner = AsyncConnection | AsyncSession


class SqlScenarioRepository:
    """Storage of the timed scenarios of one account.

    Args:
        session: Session the unit of work opened for this transaction.

    Returns:
        None.
    """

    def __init__(self, session: AsyncSession) -> None:
        """Initialize the repository.

        Args:
            session: Session bound to the current transaction.

        Returns:
            None.
        """
        self._session = session

    async def list_all(self, user_id: UserId) -> Sequence[Scenario]:
        """Return every scenario of an account, newest first.

        Args:
            user_id: Owner of the scenarios.

        Returns:
            Sequence[Scenario]: Stored scenarios.
        """
        result = await self._session.execute(
            select(ScenarioRow)
            .where(ScenarioRow.user_id == user_id.value)
            .order_by(ScenarioRow.created_at.desc(), ScenarioRow.id)
        )
        return [await self._restore(row) for row in result.scalars().all()]

    async def list_holding_priority(self, user_id: UserId) -> Sequence[Scenario]:
        """Return the scenarios that still outrank automation.

        Args:
            user_id: Owner of the scenarios.

        Returns:
            Sequence[Scenario]: Pending and running scenarios.
        """
        holding = (ScenarioStatus.PENDING.value, ScenarioStatus.RUNNING.value)
        result = await self._session.execute(
            select(ScenarioRow)
            .where(
                ScenarioRow.user_id == user_id.value,
                ScenarioRow.status.in_(holding),
            )
            .order_by(ScenarioRow.created_at.desc(), ScenarioRow.id)
        )
        return [await self._restore(row) for row in result.scalars().all()]

    async def get(self, user_id: UserId, scenario_id: ScenarioId) -> Scenario | None:
        """Return one scenario of an account.

        Args:
            user_id: Owner of the scenario.
            scenario_id: Identifier of the scenario.

        Returns:
            Scenario | None: Scenario, or None when the account has no such one.
        """
        row = await first_row(
            self._session,
            ScenarioRow,
            ScenarioRow.id == scenario_id.value,
            ScenarioRow.user_id == user_id.value,
        )
        return None if row is None else await self._restore(row)

    async def add(self, scenario: Scenario) -> None:
        """Store a newly scheduled scenario.

        Args:
            scenario: Scenario to persist.

        Returns:
            None.
        """
        values = mappers.row_values(ScenarioRow.__table__, mappers.scenario_to_row(scenario))
        await self._session.execute(insert(ScenarioRow.__table__).values(**values))
        await self._write_children(scenario)

    async def update(self, scenario: Scenario) -> None:
        """Store a changed scenario under a revision it has actually seen.

        The statement carries the revision the aggregate was read at, so a
        scenario that moves on an obsolete snapshot touches nothing instead of
        overwriting what an API call changed meanwhile. The actions and the
        captured states are replaced rather than merged: the aggregate holds the
        complete collections, and a row that is no longer listed was
        deliberately removed from it.

        Args:
            scenario: Scenario to persist.

        Returns:
            None.

        Raises:
            ConcurrentModificationError: When the row moved on since it was read.
        """
        row = mappers.scenario_to_row(scenario)
        result = await self._session.execute(
            update(ScenarioRow)
            .where(
                ScenarioRow.id == scenario.id.value,
                ScenarioRow.user_id == scenario.user_id.value,
                ScenarioRow.version == scenario.version,
            )
            .values(
                status=row.status,
                created_at=row.created_at,
                start_at=row.start_at,
                duration_minutes=row.duration_minutes,
                target=row.target,
                completion_behavior=row.completion_behavior,
                version=scenario.version + 1,
            )
        )
        await self._session.flush()
        if not result.rowcount:
            raise ConcurrentModificationError("scenario", scenario.id)
        scenario.version += 1
        await self._session.execute(
            delete(ScenarioActionRow).where(ScenarioActionRow.scenario_id == scenario.id.value)
        )
        await self._session.execute(
            delete(ScenarioCapturedStatusRow).where(
                ScenarioCapturedStatusRow.scenario_id == scenario.id.value
            )
        )
        await self._write_children(scenario)

    async def _restore(self, row: ScenarioRow) -> Scenario:
        """Rebuild one scenario together with its collections.

        Args:
            row: Row identifying the scenario.

        Returns:
            Scenario: Restored scenario.
        """
        action_rows = await every_row(
            self._session,
            ScenarioActionRow,
            ScenarioActionRow.scenario_id == row.id,
        )
        actions: tuple[ScenarioAction, ...] = tuple(
            mappers.action_from_row(entry)
            for entry in sorted(action_rows, key=lambda entry: entry.position)
        )
        captured_rows = await every_row(
            self._session,
            ScenarioCapturedStatusRow,
            ScenarioCapturedStatusRow.scenario_id == row.id,
        )
        captured: dict[DeviceId, DeviceStatus] = dict(
            mappers.captured_status_from_row(entry) for entry in captured_rows
        )
        return mappers.scenario_from_row(row, actions, captured)

    async def _write_children(self, scenario: Scenario) -> None:
        """Write the collection rows of one scenario.

        Args:
            scenario: Scenario whose collections are written.

        Returns:
            None.
        """
        await insert_rows(self._session, ScenarioActionRow.__table__, mappers.action_rows(scenario))
        await insert_rows(
            self._session,
            ScenarioCapturedStatusRow.__table__,
            mappers.captured_status_rows(scenario),
        )
        await self._session.flush()
