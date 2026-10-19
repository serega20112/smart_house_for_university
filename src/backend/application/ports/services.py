"""Ports of the services the application needs but must not implement.

Hashing a password, signing a session token, storing volatile state and telling
the time are all things the model and the use cases need and none of them are
business rules. They are declared here and implemented in the infrastructure
layer, which is what lets the domain stay free of cryptography and of storage.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime

from backend.domain.climate.home_state import HomeState
from backend.domain.identifiers import UserId


class PasswordHasher(ABC):
    """Turns a plain password into a stored form and compares the two."""

    @abstractmethod
    def hash(self, password: str) -> str:
        """Produce the stored form of a password.

        Args:
            password: Plain password chosen by the user.

        Returns:
            str: Self describing stored form carrying the salt and the cost.
        """

    @abstractmethod
    def verify(self, password: str, stored: str) -> bool:
        """Check a plain password against a stored one.

        Args:
            password: Plain password to check.
            stored: Stored form produced by :meth:`hash`.

        Returns:
            bool: True when the password matches.
        """


@dataclass(frozen=True, slots=True)
class IssuedSession:
    """A session handed out to a client.

    Args:
        token: Opaque signed token.
        expires_at: Moment the token stops being accepted.

    Returns:
        None.
    """

    token: str
    expires_at: datetime


class SessionTokenIssuer(ABC):
    """Issues and resolves session tokens."""

    @abstractmethod
    def issue(self, user_id: UserId) -> IssuedSession:
        """Create a new session for an account.

        Args:
            user_id: Account the session belongs to.

        Returns:
            IssuedSession: Token and its expiration moment.
        """

    @abstractmethod
    def resolve(self, token: str) -> UserId | None:
        """Return the account a token was issued for.

        Args:
            token: Token presented by the client.

        Returns:
            UserId | None: Owner of the token, or None when it is not valid.
        """


class HomeStateStore(ABC):
    """Durable home of the volatile state of the physical layer.

    The state of a home outlives the process that observed it: a restart must not
    make every board look offline, and several workers have to agree on what the
    relays are doing.
    """

    @abstractmethod
    async def load(self, user_id: UserId) -> HomeState:
        """Return the last known state of a home.

        Args:
            user_id: Owner of the home.

        Returns:
            HomeState: Stored state, empty when nothing was ever reported.
        """

    @abstractmethod
    async def save(self, state: HomeState) -> None:
        """Store the current state of a home.

        Args:
            state: State to persist.

        Returns:
            None.
        """

    @abstractmethod
    async def set_override_until(self, user_id: UserId, until: datetime | None) -> None:
        """Set or clear the manual override window of a home.

        The window is a single key with a native expiry, so nobody has to
        subtract minutes from a stored timestamp to find out whether it is over.

        Args:
            user_id: Owner of the home.
            until: Moment the window closes, or None to end it now.

        Returns:
            None.
        """

    @abstractmethod
    async def claim_summary_slot(self, user_id: UserId, key: str, window_sec: int) -> bool:
        """Take the right to send a throttled notification.

        Args:
            user_id: Owner of the home.
            key: Name of the throttle.
            window_sec: Length of the window in seconds.

        Returns:
            bool: True when this caller took the slot and may send now.
        """


class Clock(ABC):
    """Source of the current time."""

    @abstractmethod
    def now(self) -> datetime:
        """Return the current moment in UTC.

        Returns:
            datetime: Current moment.
        """
