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
    """Transaction over the accounts, and over nothing else.

    Args:
        session_factory: Factory producing the session of the block.

    Returns:
        None.
    """

    @property
    def accounts(self) -> AccountRepository:
        """Return the account repository bound to the current transaction.

        Returns:
            AccountRepository: Account repository.
        """
        return self.repository(SqlAccountRepository)


def make_account_unit_of_work(
    session_factory: async_sessionmaker[AsyncSession],
) -> AccountUnitOfWorkFactory:
    """Build the factory producing units of work over the accounts.

    Args:
        session_factory: Factory producing sessions.

    Returns:
        AccountUnitOfWorkFactory: Callable handing out a fresh unit of work.
    """

    def factory() -> SqlAccountUnitOfWork:
        """Create a new unit of work over the accounts.

        Returns:
            SqlAccountUnitOfWork: Unit of work bound to its own session.
        """
        return SqlAccountUnitOfWork(session_factory)

    return factory
