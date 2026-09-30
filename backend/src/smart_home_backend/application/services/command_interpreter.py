"""Natural language command interpreter.

Runs the two pipeline stages in order and applies the confidence policy, so the
use case receives an intent that is already cleared for execution. Understanding
free text belongs here rather than in a use case, which keeps the text pipeline
replaceable without touching business rules.
"""

from __future__ import annotations

from dataclasses import dataclass

from smart_home_backend.application.interface.services import (
    CommandParser,
    IntentClassifier,
    ParsedCommand,
)
from smart_home_backend.domain.enums.intent import Intent
from smart_home_backend.domain.enums.operation import ClarificationReason
from smart_home_backend.domain.policies import clarification_reason


@dataclass(frozen=True, slots=True)
class CommandInterpretation:
    """Result of the natural language pipeline.

    Args:
        intent: Intent cleared for execution, or None when the command is not
            understood well enough to act.
        parameters: Parameters extracted from the text.
        confidence: Similarity of the closest reference phrase.
        clarification: Why the user has to be asked for more detail, if needed.

    Returns:
        None.
    """

    intent: Intent | None
    parameters: ParsedCommand
    confidence: float
    clarification: ClarificationReason | None = None

    @property
    def is_executable(self) -> bool:
        """Return whether the command may be executed.

        Returns:
            bool: True when an intent was recognized with enough confidence.
        """
        return self.intent is not None and self.clarification is None


class CommandInterpreter:
    """Turns free-form text into a structured, confidence checked command."""

    def __init__(
        self,
        classifier: IntentClassifier,
        parser: CommandParser,
        confidence_threshold: float,
    ) -> None:
        """Initialize the interpreter.

        Args:
            classifier: Stage one, text to intent.
            parser: Stage two, text to command parameters.
            confidence_threshold: Similarity required to change the home.

        Returns:
            None.
        """
        self._classifier = classifier
        self._parser = parser
        self._confidence_threshold = confidence_threshold

    async def interpret(self, text: str) -> CommandInterpretation:
        """Interpret a command.

        Args:
            text: Raw command text.

        Returns:
            CommandInterpretation: Structured command or a clarification request.
        """
        prediction = await self._classifier.classify(text)
        parameters = self._parser.parse(text, prediction)
        intent = Intent.parse(prediction.intent)
        confidence = prediction.confidence
        return CommandInterpretation(
            intent=intent,
            parameters=parameters,
            confidence=confidence,
            clarification=clarification_reason(intent, confidence, self._confidence_threshold),
        )
