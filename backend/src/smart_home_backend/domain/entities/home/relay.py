"""Physical relay channel entity."""

from __future__ import annotations

from dataclasses import dataclass

from smart_home_backend.domain.enums.device import RelayState


@dataclass(frozen=True, slots=True)
class Relay:
    """Physical relay channel.

    Args:
        channel: Channel number.
        state: Current relay state.

    Returns:
        None.
    """

    channel: int
    state: RelayState = RelayState.OFF

    @property
    def is_on(self) -> bool:
        """Return whether the relay is energized.

        Returns:
            bool: True when the relay is on.
        """
        return self.state is RelayState.ON

    @classmethod
    def from_bool(cls, channel: int, on: bool) -> "Relay":
        """Build a relay from a boolean state.

        Args:
            channel: Channel number.
            on: Whether the relay is energized.

        Returns:
            Relay: Relay instance.
        """
        return cls(channel=channel, state=RelayState.ON if on else RelayState.OFF)

    def to_bool(self) -> bool:
        """Return the relay state as a boolean.

        Returns:
            bool: True when the relay is on.
        """
        return self.is_on
