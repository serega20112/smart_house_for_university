"""Inbound board data handler port.

The board connection lives in the infrastructure layer and forwards every
incoming message and connection transition through this port, so the transport
never reaches into application state directly.
"""

from __future__ import annotations

from abc import ABC, abstractmethod


class EspStateHandler(ABC):
    """Consumer of everything the board reports."""

    @abstractmethod
    async def on_connected(self) -> None:
        """Handle a new board connection.

        Returns:
            None.
        """

    @abstractmethod
    async def on_disconnected(self) -> None:
        """Handle a lost board connection.

        Returns:
            None.
        """

    @abstractmethod
    async def on_relay_states(self, states: list[bool]) -> None:
        """Handle reported relay states.

        Args:
            states: Relay states ordered by channel.

        Returns:
            None.
        """

    @abstractmethod
    async def on_reading(self, temperature: float | None, humidity: float | None) -> None:
        """Handle reported sensor readings.

        Args:
            temperature: Measured temperature or None.
            humidity: Measured relative humidity or None.

        Returns:
            None.
        """

    @abstractmethod
    async def on_error(self, code: str, message: str) -> None:
        """Handle an error reported by the board.

        Args:
            code: Machine readable error code.
            message: Human readable error description.

        Returns:
            None.
        """
