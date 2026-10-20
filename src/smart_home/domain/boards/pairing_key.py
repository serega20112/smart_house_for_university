"""Secret a board presents while dialing in.

The key is the credential of a board, so it is a value object that refuses
malformed input once instead of letting a typo become a board that can never
connect.
"""

from __future__ import annotations

import re
import secrets
from dataclasses import dataclass
from typing import Self

from smart_home.domain.exceptions import InvalidPairingKeyError

PATTERN = re.compile(r"^[A-Za-z0-9]{8,64}$")


@dataclass(frozen=True, slots=True, order=True)
class PairingKey:
    """The secret linking a board to an account.

    Args:
        value: Key as presented during the handshake.

    Returns:
        None.

    Raises:
        InvalidPairingKeyError: When the key is empty or malformed.
    """

    value: str

    def __post_init__(self) -> None:
        """Validate the shape of the key.

        Returns:
            None.

        Raises:
            InvalidPairingKeyError: When the key is empty or malformed.
        """
        trimmed = self.value.strip()
        if not trimmed:
            raise InvalidPairingKeyError("is empty")
        if not PATTERN.match(trimmed):
            raise InvalidPairingKeyError("contains characters a key cannot have")
        object.__setattr__(self, "value", trimmed)

    def __str__(self) -> str:
        """Return the masked form used in logs and messages.

        Returns:
            str: First characters followed by a fixed mask.
        """
        return f"{self.value[:4]}..."

    @classmethod
    def generate(cls) -> Self:
        """Produce a key for a board paired from the interface.

        Returns:
            Self: Fresh key.
        """
        return cls(secrets.token_hex(16))

    @classmethod
    def derive_from_chip(cls, chip_id: int) -> Self:
        """Produce the key a brand new board stores in its own flash.

        The chip identifier makes every board different without trusting any
        random source at boot, and the random tail keeps two boards flashed with
        the same firmware apart.

        Args:
            chip_id: Identifier of the chip, unique per board.

        Returns:
            Self: Key the board will present from now on.
        """
        return cls(f"{chip_id:06x}{secrets.token_hex(13)}")
