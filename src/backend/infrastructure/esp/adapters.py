"""The relay facade of the board transport.

:class:`BoardGatewayAdapter` is a thin facade over one WebSocket connection, so
that the application layer does not have to import the transport module.
"""

from __future__ import annotations

from backend.application.dto.boards.board_command_result import BoardCommandResult
from backend.application.interface.services.board_gateway import BoardGateway
from backend.domain.identifiers import EspDeviceId, UserId
from backend.domain.value_objects.boards.network_profile import NetworkProfile
from backend.infrastructure.esp.connection import EspConnection


class BoardGatewayAdapter(BoardGateway):
    """Drives the relay channels of the boards over the board connection.

    Args:
        connection: Transport level board connection.

    Returns:
        None.
    """

    def __init__(self, connection: EspConnection) -> None:
        """Initialize the adapter.

        Args:
            connection: Transport level board connection.

        Returns:
            None.
        """
        self._connection = connection

    async def set_relay(
        self, user_id: UserId, board_id: EspDeviceId, channel: int, energized: bool
    ) -> BoardCommandResult:
        """Switch a relay and wait for the confirmation.

        Args:
            user_id: Owner of the board.
            board_id: Identifier of the board.
            channel: Physical relay channel.
            energized: True to close the contact, False to release it.

        Returns:
            BoardCommandResult: What the board answered.
        """
        accepted, reason = await self._connection.set_relay(user_id, board_id, channel, energized)
        return BoardCommandResult(accepted=accepted, reason=reason)

    async def request_state(self, user_id: UserId, board_id: EspDeviceId) -> None:
        """Ask a board to resend everything it knows.

        Args:
            user_id: Owner of the board.
            board_id: Identifier of the board.

        Returns:
            None.
        """
        await self._connection.request_state(user_id, board_id)

    async def set_network(
        self, user_id: UserId, board_id: EspDeviceId, profile: NetworkProfile
    ) -> BoardCommandResult:
        """Tell a board which network it is to use.

        Args:
            user_id: Owner of the board.
            board_id: Identifier of the board.
            profile: Network the board is to use.

        Returns:
            BoardCommandResult: What the board answered.
        """
        accepted, reason = await self._connection.set_network(user_id, board_id, profile)
        return BoardCommandResult(accepted=accepted, reason=reason)

    def is_connected(self, user_id: UserId, board_id: EspDeviceId) -> bool:
        """Return whether a board currently holds a connection.

        Args:
            user_id: Owner of the board.
            board_id: Identifier of the board.

        Returns:
            bool: True when the board is connected right now.
        """
        return self._connection.is_connected(user_id, board_id)

    def board_for(self, user_id: UserId) -> EspDeviceId | None:
        """Return the account's single connected board.

        Args:
            user_id: Owner of the boards.

        Returns:
            Identifier of the board to command, or None when the account does
            not have exactly one connected board.
        """
        return self._connection.board_for(user_id)
