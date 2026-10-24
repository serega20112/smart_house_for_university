"""Чтения аккаунтов.

Чтения стороны выбора: каждое — один вопрос и один читаемый образ.
"""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncEngine

from backend.domain.identifiers import (
    UserId,
)
from backend.domain.value_objects.account.account_profile import AccountProfile
from backend.domain.value_objects.account.stored_credentials import StoredCredentials
from backend.infrastructure.database.mappers.base import as_utc
from backend.infrastructure.database.models import (
    UserModel,
)
from backend.infrastructure.database.repositories.base import first_row


class SqlAccountQueries:
    """Чтения аккаунтов без транзакции.

    Attributes:
        engine: Движок, на котором выполняют чтения.
    """

    def __init__(self, engine: AsyncEngine) -> None:
        """Инициализирует чтения.

        Args:
            engine: Движок, из которого читают.
        """
        self._engine = engine

    async def get_profile(self, user_id: UserId) -> AccountProfile | None:
        """Возвращает профиль аккаунта.

        Args:
            user_id: Владелец аккаунта.

        Returns:
            AccountProfile | None: Профиль или None, когда аккаунт исчез.
        """
        async with self._engine.connect() as connection:
            row = await first_row(connection, UserModel, UserModel.id == user_id.value)
        if row is None:
            return None
        return AccountProfile(
            id=UserId.parse(row.id),
            email=row.email,
            display_name=row.display_name,
            created_at=as_utc(row.created_at),
        )

    async def get_credentials(self, email: str) -> StoredCredentials | None:
        """Возвращает учётные данные, которым принадлежит логин.

        Сохранённый пароль — единственное, что читают здесь: профиль аккаунта —
        отдельный вопрос с отдельным ответом.

        Args:
            email: Приведённый логин аккаунта.

        Returns:
            StoredCredentials | None: Учётные данные или None, когда таким логином
            никто не пользуется.
        """
        async with self._engine.connect() as connection:
            row = await first_row(connection, UserModel, UserModel.email == email)
        if row is None:
            return None
        return StoredCredentials(user_id=UserId.parse(row.id), password_hash=row.password_hash)

    async def list_registered_ids(self) -> list[UserId]:
        """Возвращает идентификаторы каждого зарегистрированного аккаунта.

        Returns:
            list[UserId]: Зарегистрированные аккаунты.
        """
        async with self._engine.connect() as connection:
            result = await connection.execute(select(UserModel.id).order_by(UserModel.id))
            return [UserId.parse(value) for value in result.scalars().all()]
