"""A board the user paired from the interface."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class PairBoardCommand:
    """The values of a pairing the interface is asked to perform.

    Args:
        name: Name shown to the user.
        pairing_key: Key chosen by the user, or None to let the system generate
            one.

    Returns:
        None.
    """

    name: str
    pairing_key: str | None = None
