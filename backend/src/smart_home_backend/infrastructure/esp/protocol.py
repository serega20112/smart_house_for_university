"""Wire protocol spoken between the backend and the board.

Only serialization lives here: building the outgoing frames and parsing the
incoming ones. Transport concerns belong to the connection module.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from enum import StrEnum
from typing import Any

PROTOCOL_VERSION = 1

UNRECOGNIZED_MESSAGE = "unrecognized frame"


class OutboundType(StrEnum):
    """Frames the backend sends to the board."""

    SET_RELAY = "SET_RELAY"
    GET_STATE = "GET_STATE"


class InboundType(StrEnum):
    """Frames the board sends to the backend."""

    HELLO = "HELLO"
    STATE = "STATE"
    SENSOR_DATA = "SENSOR_DATA"
    ACK = "ACK"
    ERROR = "ERROR"


def build_set_relay(command_id: str, channel: int, on: bool) -> str:
    """Serialize a relay switch command.

    Args:
        command_id: Identifier used to match the acknowledgement.
        channel: Physical relay channel.
        on: New relay state.

    Returns:
        str: Serialized frame.
    """
    return json.dumps(
        {
            "type": OutboundType.SET_RELAY,
            "command_id": command_id,
            "channel": channel,
            "state": on,
        },
        ensure_ascii=False,
    )


def build_get_state() -> str:
    """Serialize a request for the full board state.

    Returns:
        str: Serialized frame.
    """
    return json.dumps({"type": OutboundType.GET_STATE}, ensure_ascii=False)


@dataclass(frozen=True, slots=True)
class InboundMessage:
    """Parsed frame received from the board.

    Args:
        type: Frame type.
        raw: Raw payload of the frame.

    Returns:
        None.
    """

    type: str
    raw: dict[str, Any]

    @property
    def relays(self) -> list[bool] | None:
        """Return the relay states carried by the frame.

        Returns:
            list[bool] | None: Relay states or None when absent.
        """
        value = self.raw.get("relays")
        return [bool(item) for item in value] if isinstance(value, list) else None

    @property
    def temperature(self) -> float | None:
        """Return the temperature carried by the frame.

        Returns:
            float | None: Temperature or None when absent.
        """
        return _as_float(self.raw.get("temperature"))

    @property
    def humidity(self) -> float | None:
        """Return the humidity carried by the frame.

        Returns:
            float | None: Humidity or None when absent.
        """
        return _as_float(self.raw.get("humidity"))

    @property
    def command_id(self) -> str | None:
        """Return the acknowledged command identifier.

        Returns:
            str | None: Command identifier or None when absent.
        """
        value = self.raw.get("command_id")
        return str(value) if value is not None else None

    @property
    def code(self) -> str:
        """Return the machine readable error code.

        Returns:
            str: Error code, empty when the frame is not an error.
        """
        return str(self.raw.get("code", ""))

    @property
    def message(self) -> str:
        """Return the human readable error description.

        Returns:
            str: Error description, empty when the frame is not an error.
        """
        return str(self.raw.get("message", ""))


def parse(raw_text: str) -> InboundMessage | None:
    """Parse an incoming frame.

    Args:
        raw_text: Raw frame received from the board.

    Returns:
        InboundMessage | None: Parsed frame or None when it is not a typed
        JSON object.
    """
    try:
        payload = json.loads(raw_text)
    except (TypeError, ValueError):
        return None
    if not isinstance(payload, dict):
        return None
    message_type = payload.get("type")
    if not isinstance(message_type, str):
        return None
    return InboundMessage(type=message_type, raw=payload)


def _as_float(value: Any) -> float | None:
    return float(value) if isinstance(value, (int, float)) and not isinstance(value, bool) else None
