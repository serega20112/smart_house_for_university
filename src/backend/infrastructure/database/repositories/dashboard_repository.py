"""Хранилище раскладки дашборда PostgreSQL."""

from __future__ import annotations

from sqlalchemy import delete
from sqlalchemy.dialects import postgresql
from sqlalchemy.ext.asyncio import AsyncConnection, AsyncSession

from backend.domain.aggregates.dashboard.dashboard_state import DashboardState
from backend.domain.identifiers import (
    UserId,
)
from backend.infrastructure.database import mappers
from backend.infrastructure.database.repositories.base import every_row, first_row, insert_rows
from backend.infrastructure.database.tables import (
    DashboardRow,
    DashboardWidgetRow,
)

UNIQUE_VIOLATION = "23505"
Runner = AsyncConnection | AsyncSession


class SqlDashboardRepository:
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
        row = await first_row(self._session, DashboardRow, DashboardRow.user_id == user_id.value)
        if row is None:
            return None
        widgets = await every_row(
            self._session,
            DashboardWidgetRow,
            DashboardWidgetRow.user_id == user_id.value,
        )
        return mappers.dashboard_from_row(row, widgets)

    async def save(self, dashboard: DashboardState) -> None:
        """Сохраняет раскладку аккаунта.

        Отметочная строка не несёт ни одной своей колонки, поэтому записать её дважды —
        пустяк, а не обновление ничего. Карточки заменяют целиком: агрегат держит
        законченный упорядоченный набор, а не заплатку к нему.

        Args:
            dashboard: Раскладка для записи.
        """
        values = mappers.row_values(DashboardRow.__table__, mappers.dashboard_to_row(dashboard))
        await self._session.execute(
            postgresql.insert(DashboardRow.__table__)
            .values(**values)
            .on_conflict_do_nothing(index_elements=[DashboardRow.__table__.c.user_id])
        )
        await self._session.execute(
            delete(DashboardWidgetRow).where(DashboardWidgetRow.user_id == dashboard.user_id.value)
        )
        await insert_rows(
            self._session, DashboardWidgetRow.__table__, mappers.widget_rows(dashboard)
        )
        await self._session.flush()
