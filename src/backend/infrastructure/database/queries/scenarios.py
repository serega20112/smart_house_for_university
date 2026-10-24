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
    """Чтения временных сценариев без транзакции.

    Attributes:
        engine: Движок, на котором выполняют чтения.
    """

    def __init__(self, engine: AsyncEngine) -> None:
        """Инициализирует чтения.

        Args:
            engine: Движок, из которого читают.
        """
        self._engine = engine

    async def list_all(self, user_id: UserId) -> list[ScenarioView]:
        """Возвращает все сценарии аккаунта.

        Args:
            user_id: Владелец сценариев.

        Returns:
            list[ScenarioView]: Сценарии, приготовленные для показа.
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
        """Возвращает сценарии, которые ещё ставят себя выше автоматики.

        Args:
            user_id: Владелец сценариев.

        Returns:
            list[ScenarioView]: Ожидающие и идущие сценарии.
        """
        return await self._holding(user_id)

    async def get(self, user_id: UserId, scenario_id: ScenarioId) -> ScenarioView | None:
        """Возвращает один сценарий аккаунта.

        Args:
            user_id: Владелец сценария.
            scenario_id: Идентификатор сценария.

        Returns:
            ScenarioView | None: Сценарий или None, когда у аккаунта такого нет.
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
        """Возвращает самый свежий сценарий, всё ещё держащий приоритет.

        Выбор следует из сохранённых данных и упорядочен по моменту просьбы, а не по
        догадке о порядке списка. Берут только последнюю строку, поэтому ответ стоит
        одинаково дорого — один в доме сценарий или сто.

        Args:
            user_id: Владелец сценариев.

        Returns:
            ScenarioView | None: Подходящий сценарий или None, когда его нет.
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
        """Возвращает сценарии аккаунта, которые ещё выше автоматики.

        Args:
            user_id: Владелец сценариев.

        Returns:
            list[ScenarioView]: Ожидающие и идущие сценарии, свежайшие в начале.
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
    """Возвращает модель чтения одного сохранённого сценария.

    Args:
        connection: Соединение, на котором выполняют чтение.
        row: Строка, которую превращают в образ.

    Returns:
        ScenarioView: Сценарий, приготовленный для показа.
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
    """Возвращает действия сохранённого сценария в объявленном им порядке.

    Args:
        connection: Соединение, на котором выполняют чтение.
        row: Строка, называющая сценарий.

    Returns:
        tuple[ScenarioAction, ...]: Действия сценария.
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
    """Возвращает состояния устройств, снятые до начала одного сценария.

    Args:
        connection: Соединение, на котором выполняют чтение.
        row: Строка, называющая сценарий.

    Returns:
        dict[DeviceId, DeviceStatus]: Идентификаторы устройств с состоянием,
        в котором они были.
    """
    stored = await every_row(
        connection,
        ScenarioCapturedStatusRow,
        ScenarioCapturedStatusRow.scenario_id == row.id,
    )
    return dict(mappers.captured_status_from_row(entry) for entry in stored)
