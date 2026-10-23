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
    """Storage of the dashboard layout of one account.

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

    async def get(self, user_id: UserId) -> DashboardState | None:
        """Return the stored layout.

        Args:
            user_id: Owner of the layout.

        Returns:
            DashboardState | None: Stored layout, or None when the account never
            customized it.
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
        """Store the layout of an account.

        The marker row carries no column of its own, so writing it twice is a
        no-op rather than an update of nothing. The widgets are replaced
        wholesale, because the aggregate holds the complete ordered layout rather
        than a patch of it.

        Args:
            dashboard: Layout to persist.

        Returns:
            None.
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
