"""Ports of the natural language pipeline.

The application declares what it needs from understanding: an intent, the
parameters the user gave, and how sure the pipeline is. Everything about how that
is achieved stays outside: the classifier, the embeddings, the similarity
threshold and the vocabulary of any language are implementation details of the
adapter that satisfies this port.

The ports live next to the DTOs they exchange, because they exist for no other
purpose than to carry these values in and out.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import StrEnum

from backend.domain.climate.temperature import Temperature
from backend.domain.devices.capability import Capability
from backend.domain.devices.device_kind import DeviceKind


class Intent(StrEnum):
    """What a user asked for.

    The vocabulary belongs to the command bus rather than to the model: these are
    the things a person may say, and the smart home itself has no opinion about
    how they are phrased.

    Args:
        None.

    Returns:
        None.
    """

    SWITCH_DEVICE = "SWITCH_DEVICE"
    SWITCH_ALL = "SWITCH_ALL"
    SET_TEMPERATURE = "SET_TEMPERATURE"
    SET_HUMIDITY = "SET_HUMIDITY"
    RUN_CAPABILITY = "RUN_CAPABILITY"
    DESCRIBE_HOME = "DESCRIBE_HOME"
    READ_TEMPERATURE = "READ_TEMPERATURE"
    READ_HUMIDITY = "READ_HUMIDITY"
    SCHEDULE_SCENARIO = "SCHEDULE_SCENARIO"
    CANCEL_SCENARIO = "CANCEL_SCENARIO"

    @property
    def changes_the_home(self) -> bool:
        """Return whether carrying the intent out touches a device.

        Intents that change something need a person to be sure they were
        understood, so a low confidence answer turns into a question instead of a
        command.

        Returns:
            bool: True for intents that change the home.
        """
        return self in _HOME_CHANGING_INTENTS

    @classmethod
    def parse(cls, raw: object) -> Intent | None:
        """Read an intent from a value produced by the pipeline.

        Args:
            raw: Intent name or enum member.

        Returns:
            Intent | None: Parsed intent, or None when nothing was recognized.
        """
        if isinstance(raw, cls):
            return raw
        if raw is None:
            return None
        try:
            return cls(str(raw).strip().upper())
        except ValueError:
            return None


_HOME_CHANGING_INTENTS: frozenset[Intent] = frozenset(
    {
        Intent.SWITCH_DEVICE,
        Intent.SWITCH_ALL,
        Intent.SET_TEMPERATURE,
        Intent.SET_HUMIDITY,
        Intent.RUN_CAPABILITY,
        Intent.SCHEDULE_SCENARIO,
        Intent.CANCEL_SCENARIO,
    }
)


class ClarificationReason(StrEnum):
    """Why a command cannot be carried out as it stands."""

    UNRECOGNIZED_INTENT = "UNRECOGNIZED_INTENT"
    LOW_CONFIDENCE = "LOW_CONFIDENCE"
    UNKNOWN_DEVICE = "UNKNOWN_DEVICE"
    MISSING_TEMPERATURE = "MISSING_TEMPERATURE"
    MISSING_HUMIDITY = "MISSING_HUMIDITY"
    MISSING_CAPABILITY = "MISSING_CAPABILITY"


@dataclass(frozen=True, slots=True)
class CommandUnderstanding:
    """What the pipeline made of a free form sentence.

    Args:
        intent: Recognized intent or None when nothing matched.
        device_name: Device name fragment found in the sentence.
        device_kinds: Device kinds the sentence could be about, offered by the
            adapter that knows the language.
        capability: Capability the sentence asks for, when it names one.
        temperature: Requested temperature.
        humidity: Requested humidity.
        delay_minutes: Requested delay before a scenario starts.
        target: Requested area or object.
        confidence: How sure the pipeline is, between zero and one.

    Returns:
        None.
    """

    intent: Intent | None = None
    device_name: str | None = None
    device_kinds: frozenset[DeviceKind] = frozenset()
    capability: Capability | None = None
    temperature: Temperature | None = None
    humidity: float | None = None
    delay_minutes: int | None = None
    target: str | None = None
    confidence: float = 0.0

    @property
    def carries_home_reference(self) -> bool:
        """Return whether the sentence names what it is about.

        Returns:
            bool: True when a device name or a device kind was recognized.
        """
        return bool(self.device_name or self.device_kinds)


class CommandUnderstandingPort(ABC):
    """Turns a free form sentence into a structured command."""

    @abstractmethod
    async def understand(self, text: str) -> CommandUnderstanding:
        """Interpret a sentence.

        Args:
            text: Raw sentence as typed or as transcribed.

        Returns:
            CommandUnderstanding: What the pipeline made of it.
        """

    @abstractmethod
    async def is_confident_enough(self, understanding: CommandUnderstanding) -> bool:
        """Return whether an understanding may be carried out.

        The threshold belongs to the adapter that knows how good its own
        classifier is, so the application never hardcodes a number that only
        makes sense for one implementation.

        Args:
            understanding: Result of the pipeline.

        Returns:
            bool: True when the command may proceed.
        """
