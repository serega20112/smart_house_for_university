"""Changing the network a board is told to use.

The owner of a board changes its network in the interface, and the backend hands
the new settings to the board over the socket it already keeps open. The board
writes them into its own flash and reconnects, which is why the settings do not
have to be pushed a second time: they live in the chip from that moment on.

The backend keeps a copy of the settings as well. That copy is what the
interface shows, what the board is asked for again after a board that was set up
on its own reports a network nobody chose, and what a board gets when it comes
back after a change it could not apply.
"""

from __future__ import annotations

from backend.application.dto.esp import BoardNetworkView, SetNetworkCommand
from backend.application.errors import BoardNotFoundError
from backend.application.ports.boards import BoardGateway
from backend.application.ports.services import Clock
from backend.application.ports.unit_of_work.board_onboarding import (
    BoardOnboardingUnitOfWorkFactory,
)
from backend.domain.boards.board_network import BoardNetwork
from backend.domain.boards.network_profile import NetworkProfile
from backend.domain.identifiers import EspDeviceId, UserId

BOARD_NETWORK_CHANGED_EVENT = "board.network_changed"


class ConfigureBoardNetworkUseCase:
    """Changes the network of a board and tells the board about it."""

    def __init__(
        self,
        onboarding_uow: BoardOnboardingUnitOfWorkFactory,
        boards: BoardGateway,
        clock: Clock,
    ) -> None:
        """Initialize the use case.

        Args:
            onboarding_uow: Factory producing transactions over the boards.
            boards: Gateway telling the boards what to do.
            clock: Source of the current time.

        Returns:
            None.
        """
        self._uow = onboarding_uow
        self._boards = boards
        self._clock = clock

    async def execute(
        self, user_id: UserId, board_id: EspDeviceId, command: SetNetworkCommand
    ) -> BoardNetworkView:
        """Store the network of a board and hand it to the board.

        The settings are stored even when the board cannot be reached: a board
        that was set up on its own has no network the backend knows of yet, and
        the owner is allowed to write the settings down before the board is
        there to receive them.

        Args:
            user_id: Owner of the board.
            board_id: Identifier of the board.
            command: Network the board is to use.

        Returns:
            BoardNetworkView: The network as the interface needs it.

        Raises:
            BoardNotFoundError: When the account has no such board.
            InvalidNetworkProfileError: When the settings cannot be used.
        """
        profile = NetworkProfile(
            ssid=command.ssid,
            password=command.password,
            host=command.host,
            server_port=command.server_port,
            socket_port=command.socket_port,
            socket_path=command.socket_path,
        )
        now = self._clock.now()

        async with self._uow() as uow:
            board = await uow.boards.get(user_id, board_id)
            if board is None:
                raise BoardNotFoundError(board_id)
            network = BoardNetwork(
                board_id=board_id,
                user_id=user_id,
                profile=profile,
                updated_at=now,
            )
            await uow.networks.save(network)

        await self._boards.set_network(user_id, board_id, profile)

        return BoardNetworkView(
            board_id=board_id,
            ssid=profile.ssid,
            host=profile.host,
            server_port=profile.server_port,
            socket_port=profile.socket_port,
            socket_path=profile.socket_path,
            configured=True,
            updated_at=now,
        )

    async def current(self, user_id: UserId, board_id: EspDeviceId) -> BoardNetworkView | None:
        """Return the network of a board as the interface needs it.

        Args:
            user_id: Owner of the board.
            board_id: Identifier of the board.

        Returns:
            BoardNetworkView | None: The network, or None when the board was
            never configured.
        """
        async with self._uow() as uow:
            board = await uow.boards.get(user_id, board_id)
            if board is None:
                raise BoardNotFoundError(board_id)
            network = await uow.networks.get(board_id)
        if network is None:
            return None
        profile = network.profile
        return BoardNetworkView(
            board_id=network.board_id,
            ssid=profile.ssid,
            host=profile.host,
            server_port=profile.server_port,
            socket_port=profile.socket_port,
            socket_path=profile.socket_path,
            configured=True,
            updated_at=network.updated_at,
        )
