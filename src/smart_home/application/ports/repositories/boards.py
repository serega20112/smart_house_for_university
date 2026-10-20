"""Board, claim and network repository ports.

Boards that already belong to an account and boards that are still asking for one
are two different things with two different lifecycles, so they get two ports
instead of one repository with a flag. The network of a board is a third thing
again: it changes on its own schedule, long after the board was taken over, so it
gets a port of its own.
"""

from __future__ import annotations

from collections.abc import Sequence
from datetime import datetime
from typing import Protocol

from smart_home.domain.boards.board_network import BoardNetwork
from smart_home.domain.boards.esp_claim import EspClaim
from smart_home.domain.boards.esp_device import EspDevice
from smart_home.domain.identifiers import EspClaimId, EspDeviceId, UserId


class BoardRepository(Protocol):
    """Storage of the boards paired with accounts."""

    async def add(self, board: EspDevice) -> None:
        """Store a newly paired board.

        Args:
            board: Board to persist.

        Returns:
            None.
        """

    async def list_for(self, user_id: UserId) -> Sequence[EspDevice]:
        """Return every board of an account.

        Args:
            user_id: Owner of the boards.

        Returns:
            Sequence[EspDevice]: Boards of the account.
        """

    async def get(self, user_id: UserId, board_id: EspDeviceId) -> EspDevice | None:
        """Return one board of an account.

        Args:
            user_id: Owner of the board.
            board_id: Identifier of the board.

        Returns:
            EspDevice | None: Board, or None when the account has no such one.
        """

    async def get_by_key(self, pairing_key: str) -> EspDevice | None:
        """Return the board presenting a pairing key.

        Args:
            pairing_key: Secret presented during the handshake.

        Returns:
            EspDevice | None: Board, or None when the key is unknown.
        """

    async def mark_seen(
        self, board_id: EspDeviceId, seen_at: datetime, ssid: str | None = None
    ) -> None:
        """Record that a board has just connected.

        Args:
            board_id: Identifier of the board.
            seen_at: Moment of the successful handshake.
            ssid: Network the board reported being on, or None when it did not
                report one.

        Returns:
            None.
        """

    async def delete(self, user_id: UserId, board_id: EspDeviceId) -> bool:
        """Remove a board of an account.

        Args:
            user_id: Owner of the board.
            board_id: Identifier of the board.

        Returns:
            bool: True when a board was removed.
        """


class ClaimRepository(Protocol):
    """Storage of the boards that announced themselves and wait for an owner."""

    async def add(self, claim: EspClaim) -> None:
        """Store a new offer.

        Args:
            claim: Offer to persist.

        Returns:
            None.
        """

    async def get_by_key(self, device_key: str) -> EspClaim | None:
        """Return the current offer of a board.

        Args:
            device_key: Secret the board presents while connecting.

        Returns:
            EspClaim | None: Offer, or None when the board never announced itself.
        """

    async def get_by_token(self, claim_token: str) -> EspClaim | None:
        """Return the offer of a token.

        Args:
            claim_token: Token shown in the interface.

        Returns:
            EspClaim | None: Offer, or None when the token is unknown.
        """

    async def list_open(self) -> Sequence[EspClaim]:
        """Return every offer nobody took yet.

        Returns:
            Sequence[EspClaim]: Open offers.
        """

    async def take(self, claim_id: EspClaimId, user_id: UserId) -> bool:
        """Record conditionally that an account took the offer.

        The write is conditional, so two accounts pressing the button at the same
        time end up with exactly one owner: the loser sees False.

        Args:
            claim_id: Identifier of the offer.
            user_id: Account taking the board.

        Returns:
            bool: True when this call was the one that claimed it.
        """

    async def delete_expired(self, before: datetime) -> int:
        """Remove the offers that are over.

        This is a command and never a side effect of reading: a caller that only
        looks at the list of offers does not change the database.

        Args:
            before: Moment the offers have to be older than.

        Returns:
            int: Number of removed offers.
        """


class BoardNetworkRepository(Protocol):
    """Storage of the network each board is told to use."""

    async def get(self, board_id: EspDeviceId) -> BoardNetwork | None:
        """Return the network of one board.

        Args:
            board_id: Identifier of the board.

        Returns:
            BoardNetwork | None: Network of that board, or None when it was
            never configured.
        """

    async def save(self, network: BoardNetwork) -> None:
        """Store the network of a board.

        Args:
            network: Network to persist.

        Returns:
            None.
        """

    async def delete(self, board_id: EspDeviceId) -> bool:
        """Remove the network of a board.

        Args:
            board_id: Identifier of the board.

        Returns:
            bool: True when a network was removed.
        """
