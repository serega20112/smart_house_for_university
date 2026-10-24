"""Чтения аккаунтов.

Чтения стороны выбора: каждое — один вопрос и один читаемый образ.
"""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from backend.application.dto.views.account_profile import AccountProfile
from backend.application.dto.views.auth_record import AuthRecord
from backend.domain.identifiers import (
    UserId,
)
from backend.infrastructure.database.mappers.base import as_utc
from backend.infrastructure.database.models import (
    UserModel,
)
from backend.infrastructure.database.repositories.base import first_row


class SqlAccountQueries:
    """Чтения аккаунтов без явной транзакции.

    Чтения идут через сессию, а не через голое соединение: только сессия гидратирует
    ORM-сущности, и потому `select(UserModel)` отдаёт строку-аккаунт, а не первый
    столбец. Реализация портов чтения совпадает здесь со способом чтения репозиториев.

    Attributes:
        session_factory: Фабрика сессий, на которой выполняют чтения.
    """

    def __init__(self, session_factory: async_sessionmaker[AsyncSession]) -> None:
        """Инициализирует чтения.

        Args:
            session_factory: Фабрика сессий, из которой читают.
        """
        self._session_factory = session_factory

    async def get_profile(self, user_id: UserId) -> AccountProfile | None:
        """Возвращает профиль аккаунта.

        Args:
            user_id: Владелец аккаунта.

        Returns:
            AccountProfile | None: Профиль или None, когда аккаунт исчез.
        """
        async with self._session_factory() as session:
            row = await first_row(session, UserModel, UserModel.id == user_id.value)
        if row is None:
            return None
        return AccountProfile(
            id=UserId.parse(row.id),
            email=row.email,
            display_name=row.display_name,
            created_at=as_utc(row.created_at),
        )

    async def get_auth_record(self, email: str) -> AuthRecord | None:
        """Возвращает учётные данные и профиль аккаунта под этим логином.

        Проверка пароля и показ профиля — один и тот же вход, поэтому они читаются
        одним запросом, а не двумя round-trip к хранилищу.

        Args:
            email: Приведённый логин аккаунта.

        Returns:
            AuthRecord | None: Учётные данные с профилем или None, когда таким логином
            никто не пользуется.
        """
        async with self._session_factory() as session:
            row = await first_row(session, UserModel, UserModel.email == email)
        if row is None:
            return None
        return AuthRecord(
            user_id=UserId.parse(row.id),
            email=row.email,
            display_name=row.display_name,
            created_at=as_utc(row.created_at),
            password_hash=row.password_hash,
        )

    async def list_registered_ids(self) -> list[UserId]:
        """Возвращает идентификаторы каждого зарегистрированного аккаунта.

        Returns:
            list[UserId]: Зарегистрированные аккаунты.
        """
        async with self._session_factory() as session:
            result = await session.execute(select(UserModel.id).order_by(UserModel.id))
            return [UserId.parse(value) for value in result.scalars().all()]
