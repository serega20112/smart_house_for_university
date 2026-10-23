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
from backend.infrastructure.database import mappers
from backend.infrastructure.database.repositories.base import first_row
from backend.infrastructure.database.tables import (
    UserRow,
)


class SqlAccountQueries:
    """Reads of the accounts, answered without a transaction.

    Args:
        engine: Engine the reads are executed on.

    Returns:
        None.
    """

    def __init__(self, engine: AsyncEngine) -> None:
        """Initialize the queries.

        Args:
            engine: Engine to read from.

        Returns:
            None.
        """
        self._engine = engine

    async def get_profile(self, user_id: UserId) -> AccountProfile | None:
        """Return the profile of an account.

        Args:
            user_id: Owner of the account.

        Returns:
            AccountProfile | None: Profile, or None when the account is gone.
        """
        async with self._engine.connect() as connection:
            row = await first_row(connection, UserRow, UserRow.id == user_id.value)
        if row is None:
            return None
        return AccountProfile(
            id=UserId.parse(row.id),
            email=row.email,
            display_name=row.display_name,
            created_at=mappers.as_utc(row.created_at),
        )

    async def get_credentials(self, email: str) -> StoredCredentials | None:
        """Return the credentials a login belongs to.

        The stored password is the only thing read here: the profile of the
        account is a separate question with a separate answer.

        Args:
            email: Normalized login of the account.

        Returns:
            StoredCredentials | None: Credentials, or None when no account uses
            that login.
        """
        async with self._engine.connect() as connection:
            row = await first_row(connection, UserRow, UserRow.email == email)
        if row is None:
            return None
        return StoredCredentials(user_id=UserId.parse(row.id), password_hash=row.password_hash)

    async def list_registered_ids(self) -> list[UserId]:
        """Return the identifiers of every registered account.

        Returns:
            list[UserId]: Registered accounts.
        """
        async with self._engine.connect() as connection:
            result = await connection.execute(select(UserRow.id).order_by(UserRow.id))
            return [UserId.parse(value) for value in result.scalars().all()]
