"""Application operations the board transport needs.

Three questions arrive from a handshake and none of them is a transport concern:
which account does this pairing key belong to, has the board just been seen, and
what should an unpaired board be told. Answering them here keeps the WebSocket
connection free of business logic and the transactions inside the collaborators
the application layer declared.

Announcing a board nobody owns is a decision of the application, so the service
that owns it is injected as a forwardable callable rather than as an object: the
service itself needs a :class:`~smart_home.application.ports.boards.BoardGateway`,
which is a facade over this very connection, and the two cannot be handed to each
other while the graph is built. The callable is resolved on the first handshake,
long after the transport exists.
"""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from dataclasses import dataclass

from smart_home.application.dto.esp import AnnounceBoardCommand
from smart_home.application.errors import ApplicationError
from smart_home.application.ports.services import Clock
from smart_home.application.ports.unit_of_work.board_onboarding import (
    BoardOnboardingUnitOfWorkFactory,
)
from smart_home.domain.boards.esp_claim import EspClaim
from smart_home.domain.exceptions import DomainError
from smart_home.domain.identifiers import EspDeviceId, UserId
from smart_home.infrastructure.logging import get_logger

log = get_logger("esp.onboarding")

AnnounceBoard = Callable[[AnnounceBoardCommand], Awaitable[EspClaim]]


@dataclass(frozen=True, slots=True)
class BoardIdentity:
    """The account a connected board belongs to.

    Args:
        user_id: Owner of the board and of the home it feeds.
        board_id: Identifier of the paired board.

    Returns:
        None.
    """

    user_id: UserId
    board_id: EspDeviceId


@dataclass(frozen=True, slots=True)
class BoardAnnouncement:
    """The offer published for a board nobody owns yet.

    Args:
        label: Short code the interface shows next to the board.
        ttl_sec: How long the offer stays valid.

    Returns:
        None.
    """

    label: str
    ttl_sec: int


class BoardOnboardingGateway:
    """Answers the questions a handshake raises, through the application layer.

    Args:
        onboarding_uow: Factory producing transactions over the boards.
        announce: Publishes or refreshes the offer of an unpaired board.
        clock: Source of the current time.

    Returns:
        None.
    """

    def __init__(
        self,
        onboarding_uow: BoardOnboardingUnitOfWorkFactory,
        announce: AnnounceBoard,
        clock: Clock,
    ) -> None:
        """Initialize the gateway.

        Args:
            onboarding_uow: Factory producing transactions over the boards.
            announce: Publishes or refreshes the offer of an unpaired board.
            clock: Source of the current time.

        Returns:
            None.
        """
        self._uow = onboarding_uow
        self._announce = announce
        self._clock = clock

    async def resolve_pairing_key(self, pairing_key: str) -> BoardIdentity | None:
        """Return the account a pairing key belongs to.

        Args:
            pairing_key: Secret the board presented during the handshake.

        Returns:
            BoardIdentity | None: Owner of the board, or None when the key is
            unknown to the server.
        """
        async with self._uow() as uow:
            board = await uow.boards.get_by_key(pairing_key)
        if board is None:
            return None
        return BoardIdentity(user_id=board.user_id, board_id=board.id)

    async def record_last_seen(self, board_id: EspDeviceId, ssid: str | None = None) -> None:
        """Record that a board has just connected.

        Args:
            board_id: Identifier of the board.
            ssid: Network the board reported being on, or None when it did not
                report one.

        Returns:
            None.
        """
        async with self._uow() as uow:
            await uow.boards.mark_seen(board_id, self._clock.now(), ssid)

    async def announce(self, device_key: str, label: str) -> BoardAnnouncement | None:
        """Publish the offer of a board nobody owns yet.

        Args:
            device_key: Secret the board presented during the handshake.
            label: Short code the board reported, possibly empty.

        Returns:
            BoardAnnouncement | None: Published offer, or None when the board
            could not be announced.
        """
        try:
            offer = await self._announce(AnnounceBoardCommand(device_key=device_key, label=label))
        except (DomainError, ApplicationError) as error:
            log.warning("board.announcement_refused", reason=str(error))
            return None
        remaining = int((offer.expires_at - self._clock.now()).total_seconds())
        return BoardAnnouncement(label=offer.label, ttl_sec=max(remaining, 1))
