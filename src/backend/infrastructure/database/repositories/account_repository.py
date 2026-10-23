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
    """Storage of the accounts of the system.

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

    async def add(self, user: User) -> None:
        """Store a new account.

        The uniqueness of the login is enforced by the store rather than by a
        lookup before the write, so two simultaneous registrations cannot both
        win. The failure is translated into a refusal of the application layer
        and the rollback is left to the unit of work.

        Args:
            user: Account to persist.

        Returns:
            None.

        Raises:
            EmailAlreadyTakenError: When the login is already registered.
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
        """Return an account by identifier.

        Args:
            user_id: Identifier of the account.

        Returns:
            User | None: Account, or None when it does not exist.
        """
        row = await first_row(self._session, UserRow, UserRow.id == user_id.value)
        return None if row is None else mappers.user_from_row(row)
