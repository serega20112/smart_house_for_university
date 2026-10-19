"""Session tokens signed with PyJWT.

Tokens are ordinary JWT documents signed with HS256. They are not stored
anywhere, so losing the signing secret logs everybody out, which is exactly what
a fresh deployment expects and what rotating a leaked secret should do.

The secret is never invented at runtime: a configuration without one is refused
before the process serves a single request.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import jwt
from jwt import InvalidTokenError

from backend.application.ports.services import IssuedSession, SessionTokenIssuer
from backend.domain.exceptions import MalformedIdentifierError
from backend.domain.identifiers import UserId

ALGORITHM = "HS256"
TOKEN_KIND = "session"
CLAIM_SUBJECT = "sub"
CLAIM_KIND = "kind"
CLAIM_ISSUED_AT = "iat"
CLAIM_EXPIRES_AT = "exp"
MINIMUM_SECRET_LENGTH = 32
LEEWAY_SECONDS = 0


class MissingSigningSecretError(RuntimeError):
    """The signing secret is missing or too short to be used.

    Args:
        message: Human readable reason.

    Returns:
        None.
    """

    def __init__(
        self, message: str = "AUTH_TOKEN_SECRET must be set and be at least 32 characters"
    ) -> None:
        """Initialize the failure.

        Args:
            message: Human readable reason.

        Returns:
            None.
        """
        super().__init__(message)


class JwtSessionTokenIssuer(SessionTokenIssuer):
    """Issues and resolves session tokens signed with HS256.

    Args:
        secret: Signing secret.
        lifetime_minutes: Validity of a freshly issued token.

    Returns:
        None.

    Raises:
        MissingSigningSecretError: When the secret is missing or too short.
    """

    def __init__(self, secret: str, lifetime_minutes: int) -> None:
        """Initialize the issuer.

        Args:
            secret: Signing secret.
            lifetime_minutes: Validity of a freshly issued token.

        Returns:
            None.

        Raises:
            MissingSigningSecretError: When the secret is missing or too short.
        """
        if len(secret) < MINIMUM_SECRET_LENGTH:
            raise MissingSigningSecretError()
        self._secret = secret
        self._lifetime = timedelta(minutes=lifetime_minutes)

    @property
    def secret(self) -> str:
        """Return the signing secret.

        Adapters that sign something narrower than a session, such as the one time
        Telegram link token, reuse it instead of asking the deployment for a
        second secret it would then have to rotate twice.

        Returns:
            str: Signing secret.
        """
        return self._secret

    def issue(self, user_id: UserId) -> IssuedSession:
        """Create a new session for an account.

        Args:
            user_id: Account the session belongs to.

        Returns:
            IssuedSession: Token and its expiration moment.
        """
        issued_at = datetime.now(UTC)
        expires_at = issued_at + self._lifetime
        token = jwt.encode(
            {
                CLAIM_SUBJECT: str(user_id),
                CLAIM_KIND: TOKEN_KIND,
                CLAIM_ISSUED_AT: int(issued_at.timestamp()),
                CLAIM_EXPIRES_AT: int(expires_at.timestamp()),
            },
            self._secret,
            algorithm=ALGORITHM,
        )
        return IssuedSession(token=token, expires_at=expires_at)

    def resolve(self, token: str) -> UserId | None:
        """Return the account a token was issued for.

        Every failure answers None: a client must not be able to tell an expired
        token from a forged one, and neither may break a request with an
        exception.

        Args:
            token: Token presented by the client.

        Returns:
            UserId | None: Owner of the token, or None when it is not valid.
        """
        try:
            claims = jwt.decode(
                token,
                self._secret,
                algorithms=[ALGORITHM],
                leeway=LEEWAY_SECONDS,
                options={"require": [CLAIM_SUBJECT, CLAIM_EXPIRES_AT]},
            )
        except InvalidTokenError:
            return None
        if claims.get(CLAIM_KIND) != TOKEN_KIND:
            return None
        try:
            return UserId.parse(str(claims[CLAIM_SUBJECT]))
        except MalformedIdentifierError:
            return None
