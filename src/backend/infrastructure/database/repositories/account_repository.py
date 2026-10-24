"""Хранилище аккаунтов PostgreSQL."""

from __future__ import annotations

from sqlalchemy import insert
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncConnection, AsyncSession

from backend.application.errors import (
    EmailAlreadyTakenError,
)
from backend.domain.aggregates.user.user import User
from backend.domain.identifiers import (
    UserId,
)
from backend.infrastructure.database import mappers
from backend.infrastructure.database.repositories.base import first_row, is_unique_violation
from backend.infrastructure.database.tables import (
    UserRow,
)

UNIQUE_VIOLATION = "23505"
Runner = AsyncConnection | AsyncSession


class SqlAccountRepository:
    """Хранение аккаунтов системы.

    Attributes:
        session: Сессия, которую открыла для этой транзакции граница.
    """

    def __init__(self, session: AsyncSession) -> None:
        """Инициализирует хранилище.

        Args:
            session: Сессия, привязанная к нынешней транзакции.
        """
        self._session = session

    async def add(self, user: User) -> None:
        """Сохраняет новый аккаунт.

        Единственность логина сторожит хранилище, а не поиск перед записью, поэтому две
        одновременные регистрации не выиграть обеим. Отказ превращается в отказ
        прикладного слоя, а откат оставляет границе транзакции.

        Args:
            user: Аккаунт для записи.

        Raises:
            EmailAlreadyTakenError: Когда логин уже зарегистрирован.
        """
        values = mappers.row_values(UserRow.__table__, mappers.user_to_row(user))
        try:
            await self._session.execute(insert(UserRow.__table__).values(**values))
            await self._session.flush()
        except IntegrityError as error:
            if not is_unique_violation(error):
                raise
            raise EmailAlreadyTakenError(user.email.value) from error

    async def get(self, user_id: UserId) -> User | None:
        """Возвращает аккаунт по идентификатору.

        Args:
            user_id: Идентификатор аккаунта.

        Returns:
            User | None: Аккаунт или None, когда его не существует.
        """
        row = await first_row(self._session, UserRow, UserRow.id == user_id.value)
        return None if row is None else mappers.user_from_row(row)
