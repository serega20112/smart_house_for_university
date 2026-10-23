"""Чтения сценариев вместе с их действиями и снятыми состояниями.

Чтения стороны выбора: каждое — один вопрос и один читаемый образ.
"""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncConnection, AsyncEngine

from backend.domain.identifiers import (
    DeviceId,
    ScenarioId,
    UserId,
)
from backend.domain.value_objects.devices.device_status import DeviceStatus
from backend.domain.value_objects.scenario.scenario_action import ScenarioAction
from backend.domain.value_objects.scenario.scenario_status import ScenarioStatus
from backend.domain.value_objects.scenario.scenario_view import ScenarioView
from backend.infrastructure.database import mappers
from backend.infrastructure.database.repositories.base import every_row, first_row
from backend.infrastructure.database.tables import (
    ScenarioActionRow,
    ScenarioCapturedStatusRow,
    ScenarioRow,
)

HOLDING_STAGES = (ScenarioStatus.PENDING.value, ScenarioStatus.RUNNING.value)


class SqlScenarioQueries:
    """Reads of the timed scenarios, answered without a transaction.

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

    async def list_all(self, user_id: UserId) -> list[ScenarioView]:
        """Return every scenario of an account.

        Args:
            user_id: Owner of the scenarios.

        Returns:
            list[ScenarioView]: Scenarios shaped for display.
        """
        async with self._engine.connect() as connection:
            result = await connection.execute(
                select(ScenarioRow)
                .where(ScenarioRow.user_id == user_id.value)
                .order_by(ScenarioRow.created_at.desc(), ScenarioRow.id)
            )
            rows = result.scalars().all()
            return [await scenario_view_of(connection, row) for row in rows]

    async def list_holding_priority(self, user_id: UserId) -> list[ScenarioView]:
        """Return the scenarios that still outrank automation.

        Args:
            user_id: Owner of the scenarios.

        Returns:
            list[ScenarioView]: Pending and running scenarios.
        """
        return await self._holding(user_id)

    async def get(self, user_id: UserId, scenario_id: ScenarioId) -> ScenarioView | None:
        """Return one scenario of an account.

        Args:
            user_id: Owner of the scenario.
            scenario_id: Identifier of the scenario.

        Returns:
            ScenarioView | None: Scenario, or None when the account has no such
            one.
        """
        async with self._engine.connect() as connection:
            row = await first_row(
                connection,
                ScenarioRow,
                ScenarioRow.id == scenario_id.value,
                ScenarioRow.user_id == user_id.value,
            )
            if row is None:
                return None
            return await scenario_view_of(connection, row)

    async def latest_holding_priority(self, user_id: UserId) -> ScenarioView | None:
        """Return the most recently scheduled scenario still holding priority.

        Choosing it is a property of the stored data, ordered by the moment the
        scenario was asked for, rather than a guess about the order of a list. Only
        the newest row is fetched, so the answer costs the same whether the home
        holds one scenario or a hundred.

        Args:
            user_id: Owner of the scenarios.

        Returns:
            ScenarioView | None: Matching scenario, or None when there is none.
        """
        async with self._engine.connect() as connection:
            result = await connection.execute(
                select(ScenarioRow)
                .where(
                    ScenarioRow.user_id == user_id.value,
                    ScenarioRow.status.in_(HOLDING_STAGES),
                )
                .order_by(ScenarioRow.created_at.desc(), ScenarioRow.id)
                .limit(1)
            )
            row = result.scalar_one_or_none()
            if row is None:
                return None
            return await scenario_view_of(connection, row)

    async def _holding(self, user_id: UserId) -> list[ScenarioView]:
        """Return the scenarios of an account that still outrank automation.

        Args:
            user_id: Owner of the scenarios.

        Returns:
            list[ScenarioView]: Pending and running scenarios, newest first.
        """
        async with self._engine.connect() as connection:
            result = await connection.execute(
                select(ScenarioRow)
                .where(
                    ScenarioRow.user_id == user_id.value,
                    ScenarioRow.status.in_(HOLDING_STAGES),
                )
                .order_by(ScenarioRow.created_at.desc(), ScenarioRow.id)
            )
            rows = result.scalars().all()
            return [await scenario_view_of(connection, row) for row in rows]


async def scenario_view_of(connection: AsyncConnection, row: ScenarioRow) -> ScenarioView:
    """Return the read model of one stored scenario.

    Args:
        connection: Connection the read is executed on.
        row: Row to shape.

    Returns:
        ScenarioView: Scenario shaped for display.
    """
    scenario = mappers.scenario_from_row(
        row,
        await scenario_actions_of(connection, row),
        await captured_statuses_of(connection, row),
    )
    return ScenarioView(
        id=scenario.id,
        status=scenario.status,
        created_at=scenario.created_at,
        start_at=scenario.start_at,
        duration_minutes=scenario.duration_minutes,
        target=scenario.target,
        completion_behavior=scenario.completion_behavior,
        actions=scenario.actions,
    )


async def scenario_actions_of(
    connection: AsyncConnection, row: ScenarioRow
) -> tuple[ScenarioAction, ...]:
    """Return the actions of one stored scenario in the order it declares.

    Args:
        connection: Connection the read is executed on.
        row: Row identifying the scenario.

    Returns:
        tuple[ScenarioAction, ...]: Actions of the scenario.
    """
    stored = await every_row(
        connection,
        ScenarioActionRow,
        ScenarioActionRow.scenario_id == row.id,
    )
    ordered = sorted(stored, key=lambda entry: entry.position)
    return tuple(mappers.action_from_row(entry) for entry in ordered)


async def captured_statuses_of(
    connection: AsyncConnection, row: ScenarioRow
) -> dict[DeviceId, DeviceStatus]:
    """Return the device states captured before one scenario started.

    Args:
        connection: Connection the read is executed on.
        row: Row identifying the scenario.

    Returns:
        dict[DeviceId, DeviceStatus]: Device identifiers mapped to the state
        they had.
    """
    stored = await every_row(
        connection,
        ScenarioCapturedStatusRow,
        ScenarioCapturedStatusRow.scenario_id == row.id,
    )
    return dict(mappers.captured_status_from_row(entry) for entry in stored)
