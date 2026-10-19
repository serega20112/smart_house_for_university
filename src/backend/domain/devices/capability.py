"""Capabilities a logical device can be asked to perform.

A capability is a command, not a state. Naming the actions instead of the relay
numbers is what lets the same automation rule work for any wiring, and it is why
the board protocol never appears in the model.
"""

from __future__ import annotations

from enum import StrEnum


class Capability(StrEnum):
    """Something the backend may ask a device to do."""

    ON = "ON"
    OFF = "OFF"
    COOL = "COOL"
    HEAT = "HEAT"
    HUMIDIFY = "HUMIDIFY"
    DEHUMIDIFY = "DEHUMIDIFY"

    @property
    def energizes_relay(self) -> bool:
        """Return whether performing the capability closes the relay contact.

        Switching something off releases the contact, everything else closes it.
        The answer is what the hardware adapter needs, and keeping it here means
        the adapter does not have to know the vocabulary.

        Returns:
            bool: True when the relay has to be closed.
        """
        return self is not Capability.OFF

    @classmethod
    def parse(cls, raw: object) -> Capability:
        """Read a capability from a value received from the outside.

        Unlike a lenient parser this one refuses an unknown name: silently turning
        a typo into a missing capability hides a broken request instead of
        answering it.

        Args:
            raw: Capability name or enum member.

        Returns:
            Capability: Parsed capability.

        Raises:
            ValueError: When the value does not name a capability.
        """
        if isinstance(raw, cls):
            return raw
        if raw is None:
            raise ValueError("capability is missing")
        return cls(str(raw).strip().upper())


class ControlSource(StrEnum):
    """Origin of a command, ordered from the highest to the lowest priority.

    Args:
        None.

    Returns:
        None.
    """

    EMERGENCY = "EMERGENCY"
    SCENARIO = "SCENARIO"
    AUTOMATION = "AUTOMATION"
    MANUAL = "MANUAL"
