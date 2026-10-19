"""State of a single physical relay contact.

The board has no modes: it has six switches. This is the only hardware level state
in the model, and it has exactly two values because that is what a contact has.
"""

from __future__ import annotations

from enum import StrEnum


class RelayState(StrEnum):
    """Position of one physical relay contact."""

    ON = "ON"
    OFF = "OFF"
