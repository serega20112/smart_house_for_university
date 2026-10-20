"""Onboarding of boards, in one place.

Announcing, taking, pairing, listing and revoking a board is one lifecycle with
five steps, so it is one cohesive service rather than five micro classes that each
open their own transaction and pass a status tuple back. Reading the list of
offers never deletes anything: removing what is over is an explicit command the
background worker runs.
"""

from __future__ import annotations

from smart_home.application.dto.esp import (
    AnnounceBoardCommand,
    BoardView,
    ClaimBoardCommand,
    PairBoardCommand,
    PairedBoard,
)
from smart_home.application.errors import BoardNotFoundError, ClaimNotFoundError
from smart_home.application.ports.boards import BoardGateway
from smart_home.application.ports.events import RealtimePublisher
from smart_home.application.ports.queries.boards import BoardQueries
from smart_home.application.ports.services import Clock
from smart_home.application.ports.unit_of_work.board_onboarding import (
    BoardOnboardingUnitOfWorkFactory,
)
from smart_home.domain.boards.esp_claim import EspClaim
from smart_home.domain.boards.esp_device import EspDevice
from smart_home.domain.boards.pairing_key import PairingKey
from smart_home.domain.exceptions import ClaimAlreadyTakenError
from smart_home.domain.identifiers import EspDeviceId, UserId

BOARD_ANNOUNCED_EVENT = "board.announcement_published"
BOARD_PAIRED_EVENT = "board.paired"


class BoardOnboardingService:
    """Owns the whole lifecycle of the boards of the system."""

    def __init__(
        self,
        onboarding_uow: BoardOnboardingUnitOfWorkFactory,
        queries: BoardQueries,
        boards: BoardGateway,
        realtime: RealtimePublisher,
        clock: Clock,
        claim_ttl_sec: int,
    ) -> None:
        """Initialize the service.

        Args:
            onboarding_uow: Factory producing transactions over the boards.
            queries: Cheap reads used to answer what the interface asks for.
            boards: Gateway telling whether a board is connected.
            realtime: Publisher of events to the open clients.
            clock: Source of the current time.
            claim_ttl_sec: How long an offer stays valid.

        Returns:
            None.
        """
        self._uow = onboarding_uow
        self._queries = queries
        self._boards = boards
        self._realtime = realtime
        self._clock = clock
        self._claim_ttl_sec = claim_ttl_sec

    async def announce(self, command: AnnounceBoardCommand) -> EspClaim:
        """Publish or refresh the offer of a board nobody owns.

        A board that announces itself again while its offer is still open keeps the
        same offer, so the code the user is looking at stays the code the board is
        asking for instead of turning into a race between two unseen tokens.

        Args:
            command: Key and label the board presented.

        Returns:
            EspClaim: Open offer of that board.
        """
        key = PairingKey(command.device_key)
        now = self._clock.now()
        async with self._uow() as uow:
            current = await uow.claims.get_by_key(key.value)
            if current is not None and current.is_valid_at(now):
                return current
            label = command.label or EspClaim.label_from_key(key)
            offer = EspClaim.announce(key, label, now, self._claim_ttl_sec)
            await uow.claims.add(offer)
        await self._realtime.broadcast(
            BOARD_ANNOUNCED_EVENT,
            {
                "label": offer.label,
                "claim_token": offer.claim_token,
                "expires_at": offer.expires_at.isoformat(),
            },
        )
        return offer

    async def claim(self, user_id: UserId, command: ClaimBoardCommand) -> BoardView:
        """Take an announced board for an account.

        The takeover is the only way a board becomes owned, and it writes the offer
        and the board in the same transaction, so the very next dial in of the board
        already resolves to an account.

        Args:
            user_id: Account taking the board.
            command: Token of the offer and the chosen name.

        Returns:
            BoardView: The board that is now owned.

        Raises:
            ClaimNotFoundError: When the token is unknown.
            ClaimExpiredError: When the offer is over.
            ClaimAlreadyTakenError: When somebody else took the board first.
        """
        now = self._clock.now()
        async with self._uow() as uow:
            offer = await uow.claims.get_by_token(command.claim_token)
            if offer is None:
                raise ClaimNotFoundError(command.claim_token)
            offer.refuse_if_not_usable(now)
            taken = await uow.claims.take(offer.id, user_id)
            if not taken:
                raise ClaimAlreadyTakenError()
            board = EspDevice.pair(
                user_id=user_id,
                name=command.name,
                pairing_key=offer.device_key,
                paired_at=now,
            )
            await uow.boards.add(board)
        await self._realtime.publish(
            user_id,
            BOARD_PAIRED_EVENT,
            {"board_id": str(board.id), "name": board.name},
        )
        return BoardView(id=board.id, name=board.name, online=False, last_seen_at=None)

    async def pair(self, user_id: UserId, command: PairBoardCommand) -> PairedBoard:
        """Pair a board from the interface and return its key exactly once.

        Args:
            user_id: Account the board belongs to.
            command: Board name and an optional key chosen by the user.

        Returns:
            PairedBoard: The board together with the key it has to present.

        Raises:
            InvalidPairingKeyError: When a provided key is malformed.
        """
        key = (
            PairingKey.generate()
            if command.pairing_key is None
            else PairingKey(command.pairing_key)
        )
        async with self._uow() as uow:
            board = EspDevice.pair(
                user_id=user_id,
                name=command.name,
                pairing_key=key,
                paired_at=self._clock.now(),
            )
            await uow.boards.add(board)
        return PairedBoard(
            board=BoardView(id=board.id, name=board.name, online=False, last_seen_at=None),
            pairing_key=key.value,
        )

    async def revoke(self, user_id: UserId, board_id: EspDeviceId) -> None:
        """Remove a board from an account.

        Args:
            user_id: Owner of the board.
            board_id: Identifier of the board.

        Returns:
            None.

        Raises:
            BoardNotFoundError: When the account has no such board.
        """
        async with self._uow() as uow:
            removed = await uow.boards.delete(user_id, board_id)
        if not removed:
            raise BoardNotFoundError(board_id)

    async def purge_expired_claims(self) -> int:
        """Remove the offers that are over.

        This is an explicit command the background worker runs, which is why a
        plain listing of the offers changes nothing in the database.

        Returns:
            int: Number of removed offers.
        """
        async with self._uow() as uow:
            return await uow.claims.delete_expired(self._clock.now())
