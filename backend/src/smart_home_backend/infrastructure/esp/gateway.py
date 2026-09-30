"""Adapter implementing the hardware gateway port over the board connection."""

from __future__ import annotations

from smart_home_backend.application.interface.services import CommandOutcome, EspGateway
from smart_home_backend.infrastructure.esp.connection import EspConnection


class EspGatewayAdapter(EspGateway):
    """Adapts the WebSocket connection to the gateway port."""

    def __init__(self, connection: EspConnection) -> None:
        """Initialize the adapter.

        Args:
            connection: Transport level board connection.

        Returns:
            None.
        """
        self._connection = connection

    async def set_relay(self, channel: int, on: bool) -> CommandOutcome:
        """Switch a relay and wait for the acknowledgement.

        Args:
            channel: Physical relay channel.
            on: New relay state.

        Returns:
            CommandOutcome: Result of the command.
        """
        return await self._connection.set_relay(channel, on)

    async def request_state(self) -> None:
        """Ask the board to resend its full state.

        Returns:
            None.
        """
        await self._connection.request_state()
