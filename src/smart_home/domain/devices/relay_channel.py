"""Number of a physical relay channel.

A channel is a position on the board, so it is a value object rather than a bare
integer: it refuses an impossible number once, at construction, instead of letting
an out of range relay number travel through a use case into a command.
"""

from __future__ import annotations

from dataclasses import dataclass

from smart_home.domain.exceptions import InvalidRelayChannelError

FIRST_CHANNEL = 1
PHYSICAL_RELAY_LIMIT = 32


@dataclass(frozen=True, slots=True, order=True)
class RelayChannel:
    """One physical relay channel of a board.

    Args:
        number: Channel number, starting at one.

    Returns:
        None.

    Raises:
        InvalidRelayChannelError: When the board has no such channel.
    """

    number: int

    def __post_init__(self) -> None:
        """Validate that the board has this channel.

        Returns:
            None.

        Raises:
            InvalidRelayChannelError: When the number is outside the hardware.
        """
        if not FIRST_CHANNEL <= self.number <= PHYSICAL_RELAY_LIMIT:
            raise InvalidRelayChannelError(self.number, PHYSICAL_RELAY_LIMIT)

    def __int__(self) -> int:
        """Return the channel number.

        Returns:
            int: Channel number.
        """
        return self.number
