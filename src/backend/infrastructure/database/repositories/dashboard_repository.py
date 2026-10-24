"""Хранилище раскладки дашборда PostgreSQL."""

from __future__ import annotations

from sqlalchemy import delete
from sqlalchemy.dialects import postgresql
from sqlalchemy.ext.asyncio import AsyncConnection, AsyncSession

from backend.application.interfaces.repositories.dashboard_repository import DashboardRepository
from backend.domain.aggregates.dashboard.dashboard_state import DashboardState
from backend.domain.identifiers import (
    UserId,
)
from backend.infrastructure.database.mappers.dashboard import (
    dashboard_from_row,
    dashboard_to_row,
    widget_rows,
)
from backend.infrastructure.database.models import (
    DashboardModel,
    DashboardWidgetModel,
)
from backend.infrastructure.database.repositories.base import (
    every_row,
    first_row,
    insert_rows,
    row_values,
)

UNIQUE_VIOLATION = "23505"
Runner = AsyncConnection | AsyncSession


class SqlDashboardRepository(DashboardRepository):
    """Хранение раскладки главного экрана одного аккаунта.

    Attributes:
        session: Сессия, которую открыла для этой транзакции граница.
    """

    def __init__(self, session: AsyncSession) -> None:
        """Инициализирует хранилище.

        Args:
            session: Сессия, привязанная к нынешней транзакции.
        """
        self._session = session

    async def get(self, user_id: UserId) -> DashboardState | None:
        """Возвращает сохранённую раскладку.

        Args:
            user_id: Владелец раскладки.

        Returns:
            DashboardState | None: Сохранённая раскладка или None, когда аккаунт её
            ни разу не настраивал.
        """
        row = await first_row(
            self._session, DashboardModel, DashboardModel.user_id == user_id.value
        )
        if row is None:
            return None
        widgets = await every_row(
            self._session,
            DashboardWidgetModel,
            DashboardWidgetModel.user_id == user_id.value,
        )
        return dashboard_from_row(row, widgets)

    async def save(self, dashboard: DashboardState) -> None:
        """Сохраняет раскладку аккаунта.

        Отметочная строка не несёт ни одной своей колонки, поэтому записать её дважды —
        пустяк, а не обновление ничего. Карточки заменяют целиком: агрегат держит
        законченный упорядоченный набор, а не заплатку к нему.

        Args:
            dashboard: Раскладка для записи.
        """
        values = row_values(DashboardModel.__table__, dashboard_to_row(dashboard))
        await self._session.execute(
            postgresql.insert(DashboardModel.__table__)
            .values(**values)
            .on_conflict_do_nothing(index_elements=[DashboardModel.__table__.c.user_id])
        )
        await self._session.execute(
            delete(DashboardWidgetModel).where(
                DashboardWidgetModel.user_id == dashboard.user_id.value
            )
        )
        await insert_rows(self._session, DashboardWidgetModel.__table__, widget_rows(dashboard))
        await self._session.flush()
