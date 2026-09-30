"""Natural language understanding ports.

The application declares the contract of the two pipeline stages while the
infrastructure layer provides the embeddings classifier and the rule based
parameter parser. Language models are not part of the pipeline.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class IntentPrediction:
    """Predicted intent with its similarity to the closest reference phrase.

    Args:
        intent: Canonical intent name or UNKNOWN when nothing matched.
        confidence: Similarity between zero and one.
        matched_example: Closest reference phrase, useful for diagnostics.

    Returns:
        None.
    """

    intent: str
    confidence: float
    matched_example: str | None = None


@dataclass(frozen=True, slots=True)
class ParsedCommand:
    """Structured command produced by the parameter parser.

    Args:
        intent: Canonical intent name reported by the classifier.
        confidence: Similarity reported by the classifier.
        device_ref: Device name fragment found in the text.
        temperature: Requested temperature in degrees Celsius.
        humidity: Requested relative humidity in percent.
        duration_minutes: Requested delay in minutes.
        target: Requested target area or object.
        raw_text: Original command text.

    Returns:
        None.
    """

    intent: str
    confidence: float
    device_ref: str | None = None
    temperature: float | None = None
    humidity: float | None = None
    duration_minutes: int | None = None
    target: str | None = None
    raw_text: str = ""


class IntentClassifier(ABC):
    """Stage one of the pipeline: text to intent."""

    @abstractmethod
    async def classify(self, text: str) -> IntentPrediction:
        """Predict the intent of a free-form command.

        Args:
            text: Raw command text.

        Returns:
            IntentPrediction: Predicted intent and confidence.
        """


class CommandParser(ABC):
    """Stage two of the pipeline: text to command parameters."""

    @abstractmethod
    def parse(self, text: str, prediction: IntentPrediction) -> ParsedCommand:
        """Extract the parameters of a command.

        Args:
            text: Raw command text.
            prediction: Prediction produced by the classifier.

        Returns:
            ParsedCommand: Structured command.
        """
