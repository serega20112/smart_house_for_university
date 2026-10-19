"""Frames of the microphone part of the board protocol."""

from __future__ import annotations

import json

from smart_home_backend.infrastructure.esp import protocol


def test_arm_mic_carries_the_rate_the_board_has_to_use() -> None:
    frame = json.loads(protocol.build_arm_mic(sample_rate=16000, max_sec=8))

    assert frame["type"] == "ARM_MIC"
    assert frame["sample_rate"] == 16000
    assert frame["max_ms"] == 8000
    assert frame["format"] == "pcm_s16le"


def test_disarm_mic_is_a_bare_frame() -> None:
    assert json.loads(protocol.build_disarm_mic()) == {"type": "DISARM_MIC"}


def test_set_vad_carries_the_threshold() -> None:
    frame = json.loads(protocol.build_set_vad(240))

    assert frame["type"] == "SET_VAD"
    assert frame["threshold"] == 240


def test_audio_start_is_parsed_with_its_rate() -> None:
    message = protocol.parse('{"type":"AUDIO_START","sample_rate":8000,"format":"pcm_s16le"}')

    assert message is not None
    assert message.type == protocol.InboundType.AUDIO_START
    assert message.sample_rate == 8000


def test_audio_start_without_a_rate_falls_back_to_the_default() -> None:
    message = protocol.parse('{"type":"AUDIO_START"}')

    assert message is not None
    assert message.sample_rate == protocol.DEFAULT_SAMPLE_RATE


def test_audio_stop_carries_its_reason() -> None:
    message = protocol.parse('{"type":"AUDIO_STOP","reason":"silence"}')

    assert message is not None
    assert message.type == protocol.InboundType.AUDIO_STOP
    assert message.reason == "silence"


def test_audio_stop_without_a_reason_is_reported_as_stopped() -> None:
    message = protocol.parse('{"type":"AUDIO_STOP"}')

    assert message is not None
    assert message.reason == ""


def test_microphone_error_reuses_the_error_frame() -> None:
    message = protocol.parse('{"type":"MIC_ERROR","code":"ADC_FAIL","message":"no samples"}')

    assert message is not None
    assert message.type == protocol.InboundType.MIC_ERROR
    assert message.code == "ADC_FAIL"
    assert message.message == "no samples"


def test_hello_announces_whether_a_microphone_is_fitted() -> None:
    message = protocol.parse('{"type":"HELLO","mic":true}')
    without = protocol.parse('{"type":"HELLO"}')

    assert message is not None and without is not None
    assert message.has_mic is True
    assert without.has_mic is False


def test_protocol_version_is_two() -> None:
    assert protocol.PROTOCOL_VERSION == 2