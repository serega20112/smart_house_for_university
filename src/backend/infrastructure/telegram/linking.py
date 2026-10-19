"""Short lived tokens that link a Telegram chat with an account.

The bot never sees a password. Linking happens over HTTP: the web interface asks
for a token, sends the user to the bot with it, and the bot answers with the
account the token names.

The token is deliberately *not* a session token. A session token is valid for
days and authorizes every request, while this one lives for minutes and carries
nothing but the account it links, so a token that ends up in a chat history or in
a screenshot is worthless a few minutes later.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import jwt
from jwt import InvalidTokenError

from backend.application.ports.services import SessionTokenIssuer
from backend.domain.exceptions import MalformedIdentifierError
from backend.domain.identifiers import UserId
from backend.infrastructure.logging import get_logger
from backend.infrastructure.security.session_tokens import MissingSigningSecretError

log = get_logger("telegram.linking")

ALGORITHM = "HS256"
LINK_KIND = "telegram_link"
CLAIM_SUBJECT = "sub"
CLAIM_KIND = "kind"
CLAIM_ISSUED_AT = "iat"
CLAIM_EXPIRES_AT = "exp"
LINK_LIFETIME_MIN = 10


class TelegramLinkTokenIssuer:
    """Issues and resolves the one time link tokens of the bot.

    Args:
        sessions: Issuer of the session tokens, whose secret and configuration
            the link tokens share so the deployment only has one secret.
        lifetime_minutes: How long a link token stays valid.

    Returns:
        None.
    """

    def __init__(
        self, sessions: SessionTokenIssuer, lifetime_minutes: int = LINK_LIFETIME_MIN
    ) -> None:
        """Initialize the issuer.

        Args:
            sessions: Issuer of the session tokens.
            lifetime_minutes: How long a link token stays valid.

        Returns:
            None.
        """
        self._sessions = sessions
        self._lifetime = timedelta(minutes=lifetime_minutes)

    def issue(self, user_id: UserId) -> str:
        """Create a one time token linking a chat to an account.

        Args:
            user_id: Account the chat is linked to.

        Returns:
            str: Signed token to send to the bot.
        """
        issued_at = datetime.now(UTC)
        expires_at = issued_at + self._lifetime
        return jwt.encode(
            {
                CLAIM_SUBJECT: str(user_id),
                CLAIM_KIND: LINK_KIND,
                CLAIM_ISSUED_AT: int(issued_at.timestamp()),
                CLAIM_EXPIRES_AT: int(expires_at.timestamp()),
            },
            _secret_of(self._sessions),
            algorithm=ALGORITHM,
        )

    def resolve(self, token: str) -> UserId | None:
        """Return the account a link token names.

        Args:
            token: Token the user sent to the bot.

        Returns:
            UserId | None: Linked account, or None when the token is not valid.
        """
        try:
            claims = jwt.decode(
                token,
                _secret_of(self._sessions),
                algorithms=[ALGORITHM],
                options={"require": [CLAIM_SUBJECT, CLAIM_EXPIRES_AT]},
            )
        except InvalidTokenError as error:
            log.info("telegram.link_token_refused", reason=type(error).__name__)
            return None
        if claims.get(CLAIM_KIND) != LINK_KIND:
            return None
        try:
            return UserId.parse(str(claims[CLAIM_SUBJECT]))
        except MalformedIdentifierError:
            return None


def _secret_of(sessions: SessionTokenIssuer) -> str:
    """Return the signing secret of a session token issuer.

    Args:
        sessions: Issuer of the session tokens.

    Returns:
        str: The shared signing secret.

    Raises:
        MissingSigningSecretError: When the issuer does not expose its secret,
            which means the deployment wired something else than the JWT issuer.
    """
    secret = getattr(sessions, "secret", None)
    if not isinstance(secret, str) or not secret:
        raise MissingSigningSecretError(
            "the session token issuer does not expose its signing secret"
        )
    return secret
