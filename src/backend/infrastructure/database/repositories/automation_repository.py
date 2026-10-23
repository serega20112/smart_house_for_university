"""Хранилище настроек автоматизации PostgreSQL."""

from __future__ import annotations

from sqlalchemy import delete
from sqlalchemy.dialects import postgresql
from sqlalchemy.ext.asyncio import AsyncConnection, AsyncSession

from backend.application.errors import (
    ConcurrentModificationError,
)
from backend.domain.aggregates.automation.automation_settings import AutomationSettings
from backend.domain.identifiers import (
    UserId,
)
from backend.infrastructure.database import mappers
from backend.infrastructure.database.repositories.base import first_row, insert_rows, upsert_columns
from backend.infrastructure.database.repositories.child_rows import participants_of
from backend.infrastructure.database.tables import (
    AutomationParticipantRow,
    AutomationRow,
)

UNIQUE_VIOLATION = "23505"
Runner = AsyncConnection | AsyncSession


class SqlAutomationRepository:
    """Storage of the automation configuration of one account.

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

    async def get(self, user_id: UserId) -> AutomationSettings | None:
        """Return the stored configuration.

        An account that never configured automation has no row, and this returns
        None instead of creating one.

        Args:
            user_id: Owner of the configuration.

        Returns:
            AutomationSettings | None: Stored configuration, or None when the
            account never configured automation.
        """
        row = await first_row(self._session, AutomationRow, AutomationRow.user_id == user_id.value)
        if row is None:
            return None
        return mappers.automation_from_row(row, await participants_of(self._session, user_id))

    async def save(self, settings: AutomationSettings) -> None:
        """Store the automation configuration of an account.

        The row is written as an upsert, so storing the configuration twice in
        one session does not collide with itself. An existing row is refreshed
        only when this writer read the revision the row still has, so a stale
        writer touches nothing instead of overwriting a newer configuration.

        Args:
            settings: Configuration to persist.

        Returns:
            None.

        Raises:
            ConcurrentModificationError: When the row moved on since it was read.
        """
        refreshed = upsert_columns(AutomationRow.__table__, "user_id", "version")
        refreshed["version"] = settings.version + 1
        values = mappers.row_values(AutomationRow.__table__, mappers.automation_to_row(settings))
        result = await self._session.execute(
            postgresql.insert(AutomationRow.__table__)
            .values(**values)
            .on_conflict_do_update(
                index_elements=[AutomationRow.__table__.c.user_id],
                set_=refreshed,
                where=AutomationRow.version == settings.version,
            )
        )
        await self._session.flush()
        if not result.rowcount:
            raise ConcurrentModificationError("automation", settings.user_id)
        settings.version += 1
        await self._session.execute(
            delete(AutomationParticipantRow).where(
                AutomationParticipantRow.user_id == settings.user_id.value
            )
        )
        await insert_rows(
            self._session,
            AutomationParticipantRow.__table__,
            mappers.participant_rows(settings),
        )
        await self._session.flush()
