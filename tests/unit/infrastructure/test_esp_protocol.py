"""Tests of the board wire protocol."""

from __future__ import annotations

import json

from smart_home_backend.infrastructure.esp.protocol import (
    InboundType,
    OutboundType,
    build_get_state,
    build_set_relay,
    parse,
)


def test_relay_command_is_serialized() -> None:
    payload = json.loads(build_set_relay("c1", 3, True))
    assert payload == {
        "type": OutboundType.SET_RELAY,
        "command_id": "c1",
        "channel": 3,
        "state": True,
    }


def test_state_request_is_serialized() -> None:
    assert json.loads(build_get_state()) == {"type": OutboundType.GET_STATE}


def test_state_frame_exposes_relays_and_reading() -> None:
    message = parse(
        json.dumps(
            {
                "type": "STATE",
                "relays": [False, True, False, False, True, False],
                "temperature": 22.4,
                "humidity": 46.2,
            }
        )
    )
    assert message is not None
    assert message.relays == [False, True, False, False, True, False]
    assert message.temperature == 22.4
    assert message.humidity == 46.2


def test_sensor_frame_carries_only_reading() -> None:
    message = parse(json.dumps({"type": "SENSOR_DATA", "temperature": 20.0, "humidity": 40.0}))
    assert message is not None
    assert message.relays is None
    assert message.type == InboundType.SENSOR_DATA


def test_error_frame_exposes_code_and_message() -> None:
    message = parse(json.dumps({"type": "ERROR", "code": "BAD", "message": "oops"}))
    assert message is not None
    assert message.code == "BAD"
    assert message.message == "oops"


def test_ack_frame_exposes_command_id() -> None:
    message = parse(json.dumps({"type": "ACK", "command_id": "c7"}))
    assert message is not None
    assert message.command_id == "c7"


def test_broken_frame_is_rejected() -> None:
    assert parse("not json") is None
    assert parse("[1, 2]") is None
    assert parse(json.dumps({"no": "type"})) is None


def test_booleans_are_not_read_as_numbers() -> None:
    message = parse(json.dumps({"type": "STATE", "temperature": True}))
    assert message is not None
    assert message.temperature is None
