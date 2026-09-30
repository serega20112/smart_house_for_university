"""Command carrying a free-form user request."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class ProcessUserCommand:
    """Input of the natural language command use case.

    Args:
        text: Raw command text written by the user.

    Returns:
        None.
    """

    text: str
