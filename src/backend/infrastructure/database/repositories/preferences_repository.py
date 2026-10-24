"""Хранилище настроек интерфейса PostgreSQL."""

from __future__ import annotations

from sqlalchemy.dialects import postgresql
from sqlalchemy.ext.asyncio import AsyncConnection, AsyncSession

from backend.domain.entities.personalization.user_preferences import UserPreferences
from backend.domain.identifiers import (
    UserId,
)
from backend.infrastructure.database.mappers.preferences import (
    preferences_from_row,
    preferences_to_row,
)
from backend.infrastructure.database.models import (
    PreferencesModel,
)
from backend.infrastructure.database.repositories.base import first_row, row_values, upsert_columns

UNIQUE_VIOLATION = "23505"
Runner = AsyncConnection | AsyncSession


class SqlPreferencesRepository:
    """Хранение настроек интерфейса одного аккаунта.

    Attributes:
        session: Сессия, которую открыла для этой транзакции граница.
    """

    def __init__(self, session: AsyncSession) -> None:
        """Инициализирует хранилище.

        Args:
            session: Сессия, привязанная к нынешней транзакции.
        """
        self._session = session

    async def get(self, user_id: UserId) -> UserPreferences | None:
        """Возвращает сохранённые настройки.

        Args:
            user_id: Владелец настроек.

        Returns:
            UserPreferences | None: Сохранённые настройки или None, когда аккаунт их
            ни разу не менял.
        """
        row = await first_row(
            self._session, PreferencesModel, PreferencesModel.user_id == user_id.value
        )
        return None if row is None else preferences_from_row(row)

    async def save(self, preferences: UserPreferences) -> None:
        """Сохраняет настройки аккаунта.

        Args:
            preferences: Настройки для записи.
        """
        values = row_values(PreferencesModel.__table__, preferences_to_row(preferences))
        await self._session.execute(
            postgresql.insert(PreferencesModel.__table__)
            .values(**values)
            .on_conflict_do_update(
                index_elements=[PreferencesModel.__table__.c.user_id],
                set_=upsert_columns(PreferencesModel.__table__, "user_id"),
            )
        )
        await self._session.flush()
