"""A free form sentence submitted by a person."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class SubmitCommand:
    """The sentence the interface was asked to carry out.

    Args:
        text: Sentence as the interface received it.

    Returns:
        None.
    """

    text: str
