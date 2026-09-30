"""Tests of the parameter parser."""

from __future__ import annotations

import pytest

from smart_home_backend.application.interface.services import IntentPrediction
from smart_home_backend.infrastructure.nlp.parser import RuleCommandParser

PREDICTION = IntentPrediction(intent="TURN_ON", confidence=0.9)


@pytest.fixture
def parser() -> RuleCommandParser:
    return RuleCommandParser()


def test_temperature_is_extracted(parser: RuleCommandParser) -> None:
    assert parser.parse("сделай 20 градусов", PREDICTION).temperature == 20.0


def test_decimal_temperature_uses_comma(parser: RuleCommandParser) -> None:
    assert parser.parse("поставь температуру 21,5", PREDICTION).temperature == 21.5


def test_humidity_is_extracted(parser: RuleCommandParser) -> None:
    parsed = parser.parse("сделай влажность 45 процентов", PREDICTION)
    assert parsed.humidity == 45.0


def test_duration_in_minutes_is_extracted(parser: RuleCommandParser) -> None:
    assert parser.parse("через 20 минут прохладно", PREDICTION).duration_minutes == 20


def test_duration_in_hours_is_converted(parser: RuleCommandParser) -> None:
    assert parser.parse("через 2 часа прохладно", PREDICTION).duration_minutes == 120


def test_half_an_hour_is_understood(parser: RuleCommandParser) -> None:
    assert parser.parse("я через полчаса приеду", PREDICTION).duration_minutes == 30


def test_missing_duration_returns_nothing(parser: RuleCommandParser) -> None:
    assert parser.parse("включи свет", PREDICTION).duration_minutes is None


def test_device_reference_is_extracted(parser: RuleCommandParser) -> None:
    assert parser.parse("выключи кондиционер", PREDICTION).device_ref == "кондиционер"


def test_light_synonyms_produce_a_reference(parser: RuleCommandParser) -> None:
    assert parser.parse("зажги лампу", PREDICTION).device_ref == "лампу"
    assert parser.parse("выключи свет", PREDICTION).device_ref == "свет"


def test_unknown_device_reference_returns_nothing(parser: RuleCommandParser) -> None:
    assert parser.parse("включи чайник", PREDICTION).device_ref is None


def test_room_target_is_detected(parser: RuleCommandParser) -> None:
    assert parser.parse("охлади комнату", PREDICTION).target == "room"


def test_plain_number_without_marker_is_ignored(parser: RuleCommandParser) -> None:
    parsed = parser.parse("включи свет 5", PREDICTION)
    assert parsed.temperature is None
    assert parsed.humidity is None


def test_out_of_range_humidity_is_ignored(parser: RuleCommandParser) -> None:
    assert parser.parse("влажность 300 процентов", PREDICTION).humidity is None
