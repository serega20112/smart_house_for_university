"""Чтения сценариев вместе с их действиями и снятыми состояниями.

Чтения стороны выбора: каждое — один вопрос и один читаемый образ.
"""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from backend.application.dto.views.scenario_view import ScenarioView
from backend.domain.entities.scenario.scenario_action import ScenarioAction
from backend.domain.identifiers import (
    DeviceId,
    ScenarioId,
    UserId,
)
from backend.domain.value_objects.devices.device_status import DeviceStatus
from backend.domain.value_objects.scenario.scenario_status import ScenarioStatus
from backend.infrastructure.database.mappers.scenario import (
    action_from_row,
    captured_status_from_row,
    scenario_from_row,
)
from backend.infrastructure.database.models import (
    ScenarioActionModel,
    ScenarioCapturedStatusModel,
    ScenarioModel,
)
from backend.infrastructure.database.repositories.base import every_row, first_row

HOLDING_STAGES = (ScenarioStatus.PENDING.value, ScenarioStatus.RUNNING.value)


class SqlScenarioQueries:
    """Чтения временных сценариев без явной транзакции.

    Чтения идут через сессию, а не через голое соединение: только сессия гидратирует
    ORM-сущности, и потому `select(ScenarioModel)` отдаёт строку-сценарий, а не первый
    столбец.

    Attributes:
        session_factory: Фабрика сессий, на которой выполняют чтения.
    """

    def __init__(self, session_factory: async_sessionmaker[AsyncSession]) -> None:
        """Инициализирует чтения.

        Args:
            session_factory: Фабрика сессий, из которой читают.
        """
        self._session_factory = session_factory

    async def list_all(self, user_id: UserId) -> list[ScenarioView]:
        """Возвращает все сценарии аккаунта.

        Args:
            user_id: Владелец сценариев.

        Returns:
            list[ScenarioView]: Сценарии, приготовленные для показа.
        """
        async with self._session_factory() as session:
            result = await session.execute(
                select(ScenarioModel)
                .where(ScenarioModel.user_id == user_id.value)
                .order_by(ScenarioModel.created_at.desc(), ScenarioModel.id)
            )
            rows = result.scalars().all()
            return [await scenario_view_of(session, row) for row in rows]

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
        async with self._session_factory() as session:
            row = await first_row(
                session,
                ScenarioModel,
                ScenarioModel.id == scenario_id.value,
                ScenarioModel.user_id == user_id.value,
            )
            if row is None:
                return None
            return await scenario_view_of(session, row)

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
        async with self._session_factory() as session:
            result = await session.execute(
                select(ScenarioModel)
                .where(
                    ScenarioModel.user_id == user_id.value,
                    ScenarioModel.status.in_(HOLDING_STAGES),
                )
                .order_by(ScenarioModel.created_at.desc(), ScenarioModel.id)
                .limit(1)
            )
            row = result.scalars().first()
            if row is None:
                return None
            return await scenario_view_of(session, row)

    async def _holding(self, user_id: UserId) -> list[ScenarioView]:
        """Возвращает сценарии аккаунта, которые ещё выше автоматики.

        Args:
            user_id: Владелец сценариев.

        Returns:
            list[ScenarioView]: Ожидающие и идущие сценарии, свежайшие в начале.
        """
        async with self._session_factory() as session:
            result = await session.execute(
                select(ScenarioModel)
                .where(
                    ScenarioModel.user_id == user_id.value,
                    ScenarioModel.status.in_(HOLDING_STAGES),
                )
                .order_by(ScenarioModel.created_at.desc(), ScenarioModel.id)
            )
            rows = result.scalars().all()
            return [await scenario_view_of(session, row) for row in rows]


async def scenario_view_of(session: AsyncSession, row: ScenarioModel) -> ScenarioView:
    """Возвращает модель чтения одного сохранённого сценария.

    Args:
        session: Сессия, на котором выполняют чтение.
        row: Строка, которую превращают в образ.

    Returns:
        ScenarioView: Сценарий, приготовленный для показа.
    """
    scenario = scenario_from_row(
        row,
        await scenario_actions_of(session, row),
        await captured_statuses_of(session, row),
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
    session: AsyncSession, row: ScenarioModel
) -> tuple[ScenarioAction, ...]:
    """Возвращает действия сохранённого сценария в объявленном им порядке.

    Args:
        session: Сессия, на котором выполняют чтение.
        row: Строка, называющая сценарий.

    Returns:
        tuple[ScenarioAction, ...]: Действия сценария.
    """
    stored = await every_row(
        session,
        ScenarioActionModel,
        ScenarioActionModel.scenario_id == row.id,
    )
    ordered = sorted(stored, key=lambda entry: entry.position)
    return tuple(action_from_row(entry) for entry in ordered)


async def captured_statuses_of(
    session: AsyncSession, row: ScenarioModel
) -> dict[DeviceId, DeviceStatus]:
    """Возвращает состояния устройств, снятые до начала одного сценария.

    Args:
        session: Сессия, на котором выполняют чтение.
        row: Строка, называющая сценарий.

    Returns:
        dict[DeviceId, DeviceStatus]: Идентификаторы устройств с состоянием,
        в котором они были.
    """
    stored = await every_row(
        session,
        ScenarioCapturedStatusModel,
        ScenarioCapturedStatusModel.scenario_id == row.id,
    )
    return dict(captured_status_from_row(entry) for entry in stored)
