"""Tests of the command interpreter."""

from __future__ import annotations

from smart_home_backend.application.interface.services import (
    CommandParser,
    IntentClassifier,
    IntentPrediction,
)
from smart_home_backend.application.services import CommandInterpreter
from smart_home_backend.domain.enums.intent import Intent
from smart_home_backend.domain.enums.operation import ClarificationReason

from tests.conftest import BASE_TIME  # noqa: F401  keeps the shared fixtures importable


class StubClassifier(IntentClassifier):
    """Classifier returning a scripted prediction."""

    def __init__(self, intent: str, confidence: float) -> None:
        self._intent = intent
        self._confidence = confidence

    async def classify(self, text: str) -> IntentPrediction:
        return IntentPrediction(intent=self._intent, confidence=self._confidence)


class StubParser(CommandParser):
    """Parser returning a fixed set of parameters."""

    def __init__(self, **parameters: object) -> None:
        self._parameters = parameters

    def parse(self, text: str, prediction: IntentPrediction):
        from smart_home_backend.application.interface.services import ParsedCommand

        return ParsedCommand(
            intent=prediction.intent,
            confidence=prediction.confidence,
            raw_text=text,
            **self._parameters,
        )


async def test_recognized_command_is_executable() -> None:
    interpreter = CommandInterpreter(
        StubClassifier("TURN_ON", 0.9), StubParser(), confidence_threshold=0.5
    )
    interpretation = await interpreter.interpret("включи свет")
    assert interpretation.intent is Intent.TURN_ON
    assert interpretation.is_executable is True


async def test_unknown_intent_requires_clarification() -> None:
    interpreter = CommandInterpreter(
        StubClassifier("SOMETHING_ELSE", 0.9), StubParser(), confidence_threshold=0.5
    )
    interpretation = await interpreter.interpret("...")
    assert interpretation.clarification is ClarificationReason.UNRECOGNIZED_INTENT
    assert interpretation.is_executable is False


async def test_low_confidence_action_requires_clarification() -> None:
    interpreter = CommandInterpreter(
        StubClassifier("TURN_ON", 0.1), StubParser(), confidence_threshold=0.5
    )
    interpretation = await interpreter.interpret("может включить")
    assert interpretation.clarification is ClarificationReason.LOW_CONFIDENCE


async def test_low_confidence_read_is_still_answered() -> None:
    interpreter = CommandInterpreter(
        StubClassifier("GET_STATUS", 0.1), StubParser(), confidence_threshold=0.5
    )
    interpretation = await interpreter.interpret("ну как там")
    assert interpretation.is_executable is True


async def test_parameters_reach_the_interpretation() -> None:
    interpreter = CommandInterpreter(
        StubClassifier("SET_TEMPERATURE", 0.9),
        StubParser(temperature=20.0, duration_minutes=30),
        confidence_threshold=0.5,
    )
    interpretation = await interpreter.interpret("сделай 20 градусов через полчаса")
    assert interpretation.parameters.temperature == 20.0
    assert interpretation.parameters.duration_minutes == 30
