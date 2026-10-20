"""Board paired with an account.

A board dials in on its own, so the only thing that links it to a person is the
key it presents during the handshake. The key is the credential, the account is
the owner of everything the board reports.

The board also tells which network it is on, and that answer is kept next to
the moment of the last handshake: both are what the board reported about itself
the last time it was seen.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Self

from smart_home.domain.boards.pairing_key import PairingKey
from smart_home.domain.exceptions import InvalidBoardNameError
from smart_home.domain.identifiers import EspDeviceId, UserId

MAX_NAME_LENGTH = 60


@dataclass(frozen=True, slots=True)
class EspDevice:
    """A board paired with one account.

    Args:
        id: Identifier assigned at creation.
        user_id: Owner of the board and of every entity it feeds.
        name: Name shown to the user.
        pairing_key: Secret the board presents while connecting.
        created_at: Moment the board was paired.
        last_seen_at: Moment of the last successful handshake, or None.
        current_ssid: Network the board reported being on, or None while it has
            not reported one.

    Returns:
        None.

    Raises:
        InvalidBoardNameError: When the name is empty or too long.
    """

    id: EspDeviceId
    user_id: UserId
    name: str
    pairing_key: PairingKey
    created_at: datetime
    last_seen_at: datetime | None = None
    current_ssid: str | None = None

    def __post_init__(self) -> None:
        """Validate the name of the board.

        Returns:
            None.

        Raises:
            InvalidBoardNameError: When the name is empty or too long.
        """
        trimmed = self.name.strip()
        if not trimmed or len(trimmed) > MAX_NAME_LENGTH:
            raise InvalidBoardNameError()
        object.__setattr__(self, "name", trimmed)

    @classmethod
    def pair(
        cls,
        user_id: UserId,
        name: str,
        pairing_key: PairingKey,
        paired_at: datetime,
    ) -> Self:
        """Build a newly paired board.

        Args:
            user_id: Owner of the board.
            name: Name shown to the user.
            pairing_key: Secret the board will present while connecting.
            paired_at: Moment of the pairing.

        Returns:
            Self: Created board.
        """
        return cls(
            id=EspDeviceId.generate(),
            user_id=user_id,
            name=name,
            pairing_key=pairing_key,
            created_at=paired_at,
        )

    def seen(self, at: datetime, ssid: str | None) -> Self:
        """Return the board as it was last seen.

        Args:
            at: Moment of the handshake.
            ssid: Network the board reported being on, or None.

        Returns:
            Self: Board carrying what it reported.
        """
        return EspDevice(
            id=self.id,
            user_id=self.user_id,
            name=self.name,
            pairing_key=self.pairing_key,
            created_at=self.created_at,
            last_seen_at=at,
            current_ssid=ssid,
        )
