import pytest

from backend.infrastructure.esp import protocol


def test_protocol_version_is_the_firmware_and_docs_version() -> None:
    assert protocol.PROTOCOL_VERSION == 3


@pytest.mark.parametrize(
    "raw",
    ["{not json", "[]", "{'type': 3}", '"SET_RELAY"', "null"],
)
def test_parse_inbound_with_unreadable_data_raises(raw: str) -> None:
    with pytest.raises(protocol.MalformedFrameError):
        protocol.parse_inbound(raw)


def test_parse_inbound_reads_a_hello_frame() -> None:
    frame = protocol.parse_inbound('{"type": "HELLO", "label": "smart relay"}')

    assert isinstance(frame, protocol.HelloFrame)
    assert frame.label == "smart relay"
    assert frame.pairing_key is None


def test_parse_inbound_reads_a_state_frame() -> None:
    frame = protocol.parse_inbound('{"type": "STATE", "relays": [true, false]}')

    assert isinstance(frame, protocol.StateFrame)
    assert frame.relays == [True, False]


def test_parse_inbound_reads_a_sensor_data_frame() -> None:
    frame = protocol.parse_inbound('{"type": "SENSOR_DATA", "temperature": 21.5}')

    assert isinstance(frame, protocol.SensorDataFrame)
    assert frame.temperature == 21.5


def test_parse_inbound_rejects_an_unknown_frame_type() -> None:
    with pytest.raises(protocol.MalformedFrameError):
        protocol.parse_inbound('{"type": "TELEPATHY"}')


def test_parse_inbound_accepts_bytes() -> None:
    frame = protocol.parse_inbound(b'{"type": "HELLO"}')

    assert isinstance(frame, protocol.HelloFrame)
