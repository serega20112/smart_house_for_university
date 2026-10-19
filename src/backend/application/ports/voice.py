"""Ports of the speech services.

The board is only a microphone: it samples its analog input and streams raw
samples over its own socket. Everything expensive happens on another machine
behind three small ports, so the backend carries no model and can be deployed
anywhere.

A clip is described by its bytes and its sample rate and nothing else: no length
arithmetic, no container headers, no limits. Those are details of the transport
and of the browser, not of a service that is handed audio and returns audio.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass

from backend.application.ports.language import CommandUnderstanding
from backend.domain.identifiers import UserId


class VoiceUnavailableError(RuntimeError):
    """The speech service could not answer.

    Args:
        message: Human readable reason.

    Returns:
        None.
    """


@dataclass(frozen=True, slots=True)
class AudioClip:
    """A piece of audio exchanged with a speech service.

    Args:
        samples: Signed sixteen bit little endian samples.
        sample_rate: Samples per second.

    Returns:
        None.
    """

    samples: bytes
    sample_rate: int


@dataclass(frozen=True, slots=True)
class Transcript:
    """Text recognized from a spoken phrase.

    Args:
        text: Recognized text, empty when the clip carried no speech.
        confidence: How sure the recognizer is.

    Returns:
        None.
    """

    text: str
    confidence: float = 1.0


class SpeechRecognizer(ABC):
    """Turns audio into text."""

    @abstractmethod
    async def transcribe(self, clip: AudioClip) -> Transcript:
        """Recognize speech in a clip.

        Args:
            clip: Audio of one phrase.

        Returns:
            Transcript: Recognized text.

        Raises:
            VoiceUnavailableError: When the service cannot answer.
        """


class SpeechSynthesizer(ABC):
    """Turns text into audio."""

    @abstractmethod
    async def synthesize(self, text: str) -> bytes:
        """Speak a phrase.

        Args:
            text: Phrase to speak.

        Returns:
            bytes: Audio of the phrase, empty when synthesis is switched off.

        Raises:
            VoiceUnavailableError: When the service cannot answer.
        """


class SpokenCommandUnderstanding(ABC):
    """Understands a transcribed sentence on the machine running the models.

    Speech arrives with far more context than a typed sentence: no punctuation,
    numbers come out as digits of a misheard word, and the speaker uses filler.
    Rule based parsing cannot recover from that, so the same machine that
    recognizes the speech is asked for a structured command first.
    """

    @abstractmethod
    async def understand(self, text: str) -> CommandUnderstanding | None:
        """Understand a transcribed sentence.

        Args:
            text: Text produced by the recognizer.

        Returns:
            CommandUnderstanding | None: Structured command, or None when the
            sentence does not describe a command at all.
        """


class ReplyComposer(ABC):
    """Produces the wording of an answer.

    Presentation owns every user facing string in this system, so the application
    asks a composer instead of writing text itself. The same strings reach the
    browser, the messenger and the speaker, which is what keeps a spoken answer
    and a typed one from drifting apart.
    """

    @abstractmethod
    def for_result(self, result: object) -> str:
        """Return what to say after a command was carried out.

        Args:
            result: Structured result of the command.

        Returns:
            str: Phrase for the user.
        """

    @abstractmethod
    def for_missing_speech(self) -> str:
        """Return what to say when nothing was recognized.

        Returns:
            str: Phrase for the user.
        """

    @abstractmethod
    def for_unavailable_service(self) -> str:
        """Return what to say when a speech service is down.

        Returns:
            str: Phrase for the user.
        """


class VoiceSession(ABC):
    """Collects the microphone stream of one board into one phrase.

    The buffering, the size limits and the decoding of the raw format belong
    behind this port, so the application never sees a sample rate, a byte count or
    a partially received phrase.
    """

    @abstractmethod
    async def begin(self, user_id: UserId, sample_rate: int) -> None:
        """Start collecting a phrase.

        Args:
            user_id: Owner of the board that is streaming.
            sample_rate: Samples per second the board streams with.

        Returns:
            None.
        """

    @abstractmethod
    async def feed(self, user_id: UserId, samples: bytes) -> None:
        """Accept the next piece of a phrase.

        Args:
            user_id: Owner of the board that is streaming.
            samples: Raw samples of the piece.

        Returns:
            None.
        """

    @abstractmethod
    async def finish(self, user_id: UserId, reason: str) -> Transcript | None:
        """Close the phrase and return what was heard.

        Args:
            user_id: Owner of the board that was streaming.
            reason: Why the board stopped.

        Returns:
            Transcript | None: What was heard, or None when the phrase carried
            nothing usable.
        """
