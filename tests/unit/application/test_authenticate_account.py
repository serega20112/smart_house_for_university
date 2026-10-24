"""Signing in never says whether an account exists.

The answer must not depend on what the server knows: an unknown login is checked
with the same cost as a known one, and a corrupted stored row is a refusal rather
than a crash. The tests stand in for the account queries and watch what reaches
the hasher.
"""

from __future__ import annotations

from datetime import UTC, datetime

import pytest
from tests.conftest import OWNER_UUID

from backend.application.dto.account.authenticate_command import AuthenticateCommand
from backend.application.dto.account.issued_session import IssuedSession
from backend.application.dto.views.account_profile import AccountProfile
from backend.application.dto.views.auth_record import AuthRecord
from backend.application.errors import InvalidCredentialsError
from backend.application.interfaces.services.security.password_hasher import PasswordHasher
from backend.application.interfaces.services.security.session_token_issuer import (
    SessionTokenIssuer,
)
from backend.application.use_cases.accounts.authenticate_account import (
    AuthenticateAccountUseCase,
)
from backend.domain.identifiers import UserId
from backend.infrastructure.security.password_hasher import Pbkdf2PasswordHasher

NOW = datetime(2026, 5, 1, 12, 0, tzinfo=UTC)
EMAIL = "owner@example.com"
STORED = "pbkdf2_sha256$100$c2FsdA$ZGl2"


class StubQueries:
    """Answers with the one auth record the test prepared.

    Args:
        record: Record the login sees, or None for an unknown account.
    """

    def __init__(self, record: AuthRecord | None) -> None:
        self._record = record

    async def get_auth_record(self, email: str) -> AuthRecord | None:
        """Return the prepared record.

        Args:
            email: Login under question.

        Returns:
            AuthRecord | None: The record, or None when nobody has this login.
        """
        del email
        return self._record


class RecordingHasher(PasswordHasher):
    """Records the stored form every check was given.

    Args:
        accepts: Verdict every check answers with, whatever was stored.
    """

    def __init__(self, accepts: bool = False) -> None:
        self._accepts = accepts
        self.checked: list[str | None] = []

    async def hash(self, password: str) -> str:
        """Return the fixed stored form of this stub.

        Args:
            password: Password to hold.

        Returns:
            str: The fixed form.
        """
        del password
        return STORED

    async def verify(self, password: str, stored: str | None) -> bool:
        """Record the stored form and answer with the prepared verdict.

        Args:
            password: Password that was typed.
            stored: Stored form, or None when the account is unknown.

        Returns:
            bool: The prepared verdict.
        """
        del password
        self.checked.append(stored)
        return self._accepts


class StubTokens(SessionTokenIssuer):
    """Issues one predictable session and resolves no token.

    Args:
        None.
    """

    def issue(self, user_id: UserId) -> IssuedSession:
        """Open a session for the account.

        Args:
            user_id: Account the session belongs to.

        Returns:
            IssuedSession: Fixed token of this stub.
        """
        del user_id
        return IssuedSession(token="session", expires_at=NOW)

    def resolve(self, token: str) -> UserId | None:
        """Resolve no token at all.

        Args:
            token: Token under question.

        Returns:
            UserId | None: Always None, nothing was issued by the real issuer.
        """
        del token
        return None


def auth_record(password_hash: str = STORED) -> AuthRecord:
    """Build the record of a known account.

    Args:
        password_hash: Stored form the login is checked against.

    Returns:
        AuthRecord: Record of the shared owner.
    """
    return AuthRecord(
        user_id=UserId.parse(OWNER_UUID),
        email=EMAIL,
        display_name="Owner",
        created_at=NOW,
        password_hash=password_hash,
    )


async def test_an_unknown_login_is_checked_as_carefully_as_a_known_one() -> None:
    hasher = RecordingHasher()
    use_case = AuthenticateAccountUseCase(StubQueries(None), hasher, StubTokens())

    with pytest.raises(InvalidCredentialsError):
        await use_case.execute(AuthenticateCommand(email=EMAIL, password="any"))

    assert hasher.checked == [None]


async def test_a_known_login_is_checked_against_its_own_stored_form() -> None:
    hasher = RecordingHasher(accepts=False)
    use_case = AuthenticateAccountUseCase(StubQueries(auth_record()), hasher, StubTokens())

    with pytest.raises(InvalidCredentialsError):
        await use_case.execute(AuthenticateCommand(email=EMAIL, password="wrong"))

    assert hasher.checked == [STORED]


async def test_a_corrupted_stored_row_is_a_refusal_and_not_a_crash() -> None:
    hasher = Pbkdf2PasswordHasher(iterations=100, salt_bytes=16)
    use_case = AuthenticateAccountUseCase(
        StubQueries(auth_record("pbkdf2_sha256$ten$c2FsdA$ZGl2")), hasher, StubTokens()
    )

    with pytest.raises(InvalidCredentialsError):
        await use_case.execute(AuthenticateCommand(email=EMAIL, password="any"))


async def test_the_right_password_opens_a_session_with_the_profile() -> None:
    hasher = Pbkdf2PasswordHasher(iterations=100, salt_bytes=16)
    stored = await hasher.hash("right horse")
    use_case = AuthenticateAccountUseCase(StubQueries(auth_record(stored)), hasher, StubTokens())

    session = await use_case.execute(AuthenticateCommand(email=EMAIL, password="right horse"))

    assert isinstance(session.profile, AccountProfile)
    assert session.profile.email == EMAIL
    assert session.token == "session"
    assert session.expires_at == NOW
