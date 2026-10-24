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
    """Хранение временных сценариев одного аккаунта.

    Attributes:
        session: Сессия, которую открыла для этой транзакции граница.
    """

    def __init__(self, session: AsyncSession) -> None:
        """Инициализирует хранилище.

        Args:
            session: Сессия, привязанная к нынешней транзакции.
        """
        self._session = session

    async def list_all(self, user_id: UserId) -> Sequence[Scenario]:
        """Возвращает все сценарии аккаунта, свежие в начале.

        Args:
            user_id: Владелец сценариев.

        Returns:
            Sequence[Scenario]: Сохранённые сценарии.
        """
        result = await self._session.execute(
            select(ScenarioRow)
            .where(ScenarioRow.user_id == user_id.value)
            .order_by(ScenarioRow.created_at.desc(), ScenarioRow.id)
        )
        return [await self._restore(row) for row in result.scalars().all()]

    async def list_holding_priority(self, user_id: UserId) -> Sequence[Scenario]:
        """Возвращает сценарии, которые ещё ставят себя выше автоматики.

        Args:
            user_id: Владелец сценариев.

        Returns:
            Sequence[Scenario]: Ожидающие и идущие сценарии.
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
        """Возвращает один сценарий аккаунта.

        Args:
            user_id: Владелец сценария.
            scenario_id: Идентификатор сценария.

        Returns:
            Scenario | None: Сценарий или None, когда у аккаунта такого нет.
        """
        row = await first_row(
            self._session,
            ScenarioRow,
            ScenarioRow.id == scenario_id.value,
            ScenarioRow.user_id == user_id.value,
        )
        return None if row is None else await self._restore(row)

    async def add(self, scenario: Scenario) -> None:
        """Сохраняет только что поставленный сценарий.

        Args:
            scenario: Сценарий для записи.
        """
        values = mappers.row_values(ScenarioRow.__table__, mappers.scenario_to_row(scenario))
        await self._session.execute(insert(ScenarioRow.__table__).values(**values))
        await self._write_children(scenario)

    async def update(self, scenario: Scenario) -> None:
        """Сохраняет изменённый сценарий по ревизии, которую он действительно видел.

        Запрос несёт ревизию, на которой агрегат прочитали, поэтому сценарий, идущий
        по устаревшему снимку, не трогает ничего вместо того, чтобы перетереть то, что
        успела изменить заявка API. Действия и снятые состояния заменяют целиком, а не
        сливают: агрегат держит коллекции полностью, и строку, которой в нём больше нет,
        из него убрали нарочно.

        Args:
            scenario: Сценарий для записи.

        Raises:
            ConcurrentModificationError: Когда строка ушла вперёд с момента чтения.
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
        """Восстанавливает один сценарий вместе с его коллекциями.

        Args:
            row: Строка, называющая сценарий.

        Returns:
            Scenario: Восстановленный сценарий.
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
        """Записывает строки коллекций одного сценария.

        Args:
            scenario: Сценарий, чьи коллекции записывают.
        """
        await insert_rows(self._session, ScenarioActionRow.__table__, mappers.action_rows(scenario))
        await insert_rows(
            self._session,
            ScenarioCapturedStatusRow.__table__,
            mappers.captured_status_rows(scenario),
        )
        await self._session.flush()
