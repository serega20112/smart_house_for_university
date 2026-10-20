"""Authorize an existing account.

The read goes through the query port rather than a transaction: authorizing
somebody is a select, and a select wrapped in a transaction is overhead with no
purpose.
"""

from __future__ import annotations

from smart_home.application.dto.account import (
    AccountProfile,
    AuthenticateCommand,
    AuthenticatedSession,
)
from smart_home.application.errors import InvalidCredentialsError
from smart_home.application.ports.queries.accounts import AccountQueries
from smart_home.application.ports.services import PasswordHasher, SessionTokenIssuer
from smart_home.domain.accounts.email import Email
from smart_home.domain.exceptions import InvalidEmailError
from smart_home.domain.identifiers import UserId


class AuthenticateAccountUseCase:
    """Checks a login and a password and issues a session token."""

    def __init__(
        self,
        queries: AccountQueries,
        hasher: PasswordHasher,
        tokens: SessionTokenIssuer,
    ) -> None:
        """Initialize the use case.

        Args:
            queries: Cheap reads of the accounts.
            hasher: Compares a plain password with a stored one.
            tokens: Issues the session token.

        Returns:
            None.
        """
        self._queries = queries
        self._hasher = hasher
        self._tokens = tokens

    async def execute(self, command: AuthenticateCommand) -> AuthenticatedSession:
        """Authorize the account and open a session for it.

        An unknown login and a wrong password produce the very same refusal, so the
        answer never reveals whether an account exists.

        Args:
            command: Credentials presented at login.

        Returns:
            AuthenticatedSession: Profile and session token.

        Raises:
            InvalidCredentialsError: When the login or the password is wrong.
        """
        try:
            email = Email.parse(command.email)
        except InvalidEmailError as error:
            raise InvalidCredentialsError() from error
        stored = await self._queries.get_credentials(email.value)
        if stored is None or not self._hasher.verify(command.password, stored.password_hash):
            raise InvalidCredentialsError()
        session = self._tokens.issue(stored.user_id)
        return AuthenticatedSession(
            profile=await self._profile_of(stored.user_id),
            token=session.token,
            expires_at=session.expires_at,
        )

    async def _profile_of(self, user_id: UserId) -> AccountProfile:
        profile = await self._queries.get_profile(user_id)
        if profile is None:
            raise InvalidCredentialsError()
        return profile
