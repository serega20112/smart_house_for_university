"""Physical hardware gateway port."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class CommandOutcome:
    """Result of a low level command sent to the board.

    Args:
        ok: Whether the command was confirmed by the board.
        error: Machine readable failure reason or None on success.

    Returns:
        None.
    """

    ok: bool
    error: str | None = None


class EspGateway(ABC):
    """Gateway driving the relay channels and reading the sensor."""

    @abstractmethod
    async def set_relay(self, channel: int, on: bool) -> CommandOutcome:
        """Switch a physical relay channel and wait for its confirmation.

        Implementations report an unreachable board as a failed outcome instead
        of raising, which keeps availability handling out of the application
        services.

        Args:
            channel: Physical relay channel.
            on: True to energize the relay, False to release it.

        Returns:
            CommandOutcome: Result of the command.
        """

    @abstractmethod
    async def request_state(self) -> None:
        """Ask the board to resend its full state.

        Returns:
            None.
        """
