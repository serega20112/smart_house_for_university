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

from smart_home.domain.climate.climate_reading import ClimateReading
from smart_home.domain.climate.home_state import HomeState
from smart_home.domain.devices.device import Device
from smart_home.domain.devices.device_status import DeviceStatus
from smart_home.domain.identifiers import DeviceId, UserId


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
    relays are doing. Every operation is a statement about the domain, applied
    atomically on the server, so two writers never erase each other's fact: no
    operation reads the whole state, changes an object and writes it back whole.
    """

    @abstractmethod
    async def read(self, user_id: UserId) -> HomeState:
        """Return the last known state of a home.

        Args:
            user_id: Owner of the home.

        Returns:
            HomeState: Stored state, empty when nothing was ever reported.
        """

    @abstractmethod
    async def record_background_reading(
        self, user_id: UserId, reading: ClimateReading, changed_at: datetime
    ) -> ClimateReading:
        """Apply a sensor report the board produced.

        Args:
            user_id: Owner of the home.
            reading: Measured values, absent where the sensor did not answer.
            changed_at: Moment the board reported them.

        Returns:
            ClimateReading: The values that actually moved.
        """

    @abstractmethod
    async def record_relay_report(
        self, user_id: UserId, states: list[bool], changed_at: datetime
    ) -> tuple[int, ...]:
        """Apply the relay positions reported by a board.

        Args:
            user_id: Owner of the board.
            states: Contact positions ordered by channel, starting at one.
            changed_at: Moment the board reported them.

        Returns:
            tuple[int, ...]: Channels whose position actually moved.
        """

    @abstractmethod
    async def record_board_online(
        self, user_id: UserId, online: bool, changed_at: datetime
    ) -> bool:
        """Record whether a board is reachable.

        Args:
            user_id: Owner of the board.
            online: True when the board answered, False when it went away.
            changed_at: Moment of the transition.

        Returns:
            bool: The reachable flag as it stood before the change, so a caller
            can tell whether the state of the home actually moved.
        """

    @abstractmethod
    async def record_command_result(
        self,
        user_id: UserId,
        device: Device,
        status: DeviceStatus,
        changed_at: datetime,
    ) -> None:
        """Store a command result the board confirmed.

        Args:
            user_id: Owner of the device.
            device: Device the command was performed on.
            status: State the device was driven into.
            changed_at: Moment of the confirmation.

        Returns:
            None.
        """

    @abstractmethod
    async def forget_device_status(self, user_id: UserId, device_id: DeviceId) -> None:
        """Drop everything remembered about a device that no longer exists.

        Args:
            user_id: Owner of the removed device.
            device_id: Identifier of the removed device.

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
