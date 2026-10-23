"""What a board said about itself while dialing in."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class AnnounceBoardCommand:
    """The identity a board presented during its handshake.

    Args:
        device_key: Secret the board presented.
        label: Short code the board reported, or an empty string.

    Returns:
        None.
    """

    device_key: str
    label: str
