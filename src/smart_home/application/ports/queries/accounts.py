"""Read side of the accounts.

Reading an account never opens a transaction. The read models here are shaped for
their consumer: a profile for the interface, which has no field for the stored
password, and a credentials pair for the login, which has no field for the display
name.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from smart_home.application.dto.account import AccountProfile
from smart_home.domain.identifiers import UserId


@dataclass(frozen=True, slots=True)
class StoredCredentials:
    """What authorizing a login needs and nothing more.

    Args:
        user_id: Account the credentials belong to.
        password_hash: Stored form of the password.

    Returns:
        None.
    """

    user_id: UserId
    password_hash: str


class AccountQueries(Protocol):
    """Reads of the accounts."""

    async def get_profile(self, user_id: UserId) -> AccountProfile | None:
        """Return the profile of an account.

        Args:
            user_id: Owner of the account.

        Returns:
            AccountProfile | None: Profile, or None when the account is gone.
        """

    async def get_credentials(self, email: str) -> StoredCredentials | None:
        """Return the credentials a login belongs to.

        Args:
            email: Normalized login of the account.

        Returns:
            StoredCredentials | None: Credentials, or None when no account uses
            that login.
        """

    async def list_registered_ids(self) -> list[UserId]:
        """Return the identifiers of every registered account.

        The background cycles need it to serve every home, while each cycle still
        runs fully inside the scope of a single account.

        Returns:
            list[UserId]: Registered accounts.
        """
