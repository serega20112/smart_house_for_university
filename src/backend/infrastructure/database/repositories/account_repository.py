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
from backend.infrastructure.database.mappers.accounts import user_from_row, user_to_row
from backend.infrastructure.database.models import (
    UserModel,
)
from backend.infrastructure.database.repositories.base import (
    first_row,
    is_unique_violation,
    row_values,
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
        values = row_values(UserModel.__table__, user_to_row(user))
        try:
            await self._session.execute(insert(UserModel.__table__).values(**values))
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
        row = await first_row(self._session, UserModel, UserModel.id == user_id.value)
        return None if row is None else user_from_row(row)
