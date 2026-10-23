"""A board the user is taking over from the interface."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class ClaimBoardCommand:
    """The values of a takeover the interface is asked to perform.

    Args:
        claim_token: Token of the offer shown next to the board.
        name: Name the user wants the board to have.

    Returns:
        None.
    """

    claim_token: str
    name: str
