"""Транзакция аккаунтов.

Границы транзакций: одна сессия, одна транзакция, свои хранилища.
"""

from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from backend.application.interface.repositories.account_repository import AccountRepository
from backend.application.interface.unit_of_work.account import (
    AccountUnitOfWork,
    AccountUnitOfWorkFactory,
)
from backend.infrastructure.database.repositories import (
    SqlAccountRepository,
)
from backend.infrastructure.database.unit_of_work.base import SqlUnitOfWork


class SqlAccountUnitOfWork(SqlUnitOfWork, AccountUnitOfWork):
    """Транзакция над аккаунтами и больше ни над чем.

    Attributes:
        session_factory: Фабрика, дающая сессию блока.
    """

    @property
    def accounts(self) -> AccountRepository:
        """Хранилище аккаунтов нынешней транзакции."""
        return self.repository(SqlAccountRepository)


def make_account_unit_of_work(
    session_factory: async_sessionmaker[AsyncSession],
) -> AccountUnitOfWorkFactory:
    """Строит фабрику границ транзакции над аккаунтами.

    Args:
        session_factory: Фабрика сессий.

    Returns:
        AccountUnitOfWorkFactory: Вызываемый объект, дающий свежую границу.
    """

    def factory() -> SqlAccountUnitOfWork:
        """Создаёт новую границу над аккаунтами."""
        return SqlAccountUnitOfWork(session_factory)

    return factory
