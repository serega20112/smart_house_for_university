"""Хранилище настроек интерфейса PostgreSQL."""

from __future__ import annotations

from sqlalchemy.dialects import postgresql
from sqlalchemy.ext.asyncio import AsyncConnection, AsyncSession

from backend.domain.aggregates.preferences.user_preferences import UserPreferences
from backend.domain.identifiers import (
    UserId,
)
from backend.infrastructure.database import mappers
from backend.infrastructure.database.repositories.base import first_row, upsert_columns
from backend.infrastructure.database.tables import (
    PreferencesRow,
)

UNIQUE_VIOLATION = "23505"
Runner = AsyncConnection | AsyncSession


class SqlPreferencesRepository:
    """Storage of the interface preferences of one account.

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

    async def get(self, user_id: UserId) -> UserPreferences | None:
        """Return the stored preferences.

        Args:
            user_id: Owner of the preferences.

        Returns:
            UserPreferences | None: Stored preferences, or None when the account
            never changed them.
        """
        row = await first_row(
            self._session, PreferencesRow, PreferencesRow.user_id == user_id.value
        )
        return None if row is None else mappers.preferences_from_row(row)

    async def save(self, preferences: UserPreferences) -> None:
        """Store the preferences of an account.

        Args:
            preferences: Preferences to persist.

        Returns:
            None.
        """
        values = mappers.row_values(
            PreferencesRow.__table__, mappers.preferences_to_row(preferences)
        )
        await self._session.execute(
            postgresql.insert(PreferencesRow.__table__)
            .values(**values)
            .on_conflict_do_update(
                index_elements=[PreferencesRow.__table__.c.user_id],
                set_=upsert_columns(PreferencesRow.__table__, "user_id"),
            )
        )
        await self._session.flush()
