"""Account repository port."""

from __future__ import annotations

from typing import Protocol

from backend.domain.accounts.user import User
from backend.domain.identifiers import UserId


class AccountRepository(Protocol):
    """Storage of the accounts of the system."""

    async def add(self, user: User) -> None:
        """Store a new account.

        Args:
            user: Account to persist.

        Returns:
            None.

        Raises:
            EmailAlreadyTakenError: When the login is already registered. The
            uniqueness is enforced by the store itself, so two simultaneous
            registrations cannot both win.
        """

    async def get(self, user_id: UserId) -> User | None:
        """Return an account by identifier.

        Args:
            user_id: Identifier of the account.

        Returns:
            User | None: Account, or None when it does not exist.
        """

    async def get_by_email(self, email: str) -> User | None:
        """Return an account by login.

        Args:
            email: Normalized login of the account.

        Returns:
            User | None: Account, or None when it does not exist.
        """
