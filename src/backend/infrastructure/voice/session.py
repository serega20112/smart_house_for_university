"""Collecting the microphone stream of a board into one phrase.

A board streams raw samples in many small pieces. The application never sees a
sample rate, a byte count or a partially received phrase, so the buffering, the
size limit and the recognition of the finished clip all happen here.
"""

from __future__ import annotations

from backend.application.ports.voice import (
    AudioClip,
    SpeechRecognizer,
    Transcript,
    VoiceSession,
    VoiceUnavailableError,
)
from backend.domain.identifiers import UserId
from backend.infrastructure.logging import get_logger

log = get_logger("voice.session")

BYTES_PER_SAMPLE = 2
DEFAULT_SAMPLE_RATE = 16000


class BufferedVoiceSession(VoiceSession):
    """Turns the pieces of a phrase into one clip and recognizes it.

    A phrase is bounded twice: by the moment the board says it stopped and by a
    hard byte budget derived from the configured sample rate and longest phrase,
    so a board that keeps streaming cannot exhaust the memory of the process.

    Args:
        recognizer: Speech recognition applied to the finished clip.
        sample_rate: Sample rate the boards are told to use.
        max_audio_sec: Longest phrase a board may send.

    Returns:
        None.
    """

    def __init__(
        self,
        recognizer: SpeechRecognizer,
        sample_rate: int,
        max_audio_sec: int,
    ) -> None:
        """Initialize the session.

        Args:
            recognizer: Speech recognition applied to the finished clip.
            sample_rate: Sample rate the boards are told to use.
            max_audio_sec: Longest phrase a board may send.

        Returns:
            None.
        """
        self._recognizer = recognizer
        self._budget = sample_rate * BYTES_PER_SAMPLE * max_audio_sec
        self._chunks: dict[UserId, bytearray] = {}
        self._rates: dict[UserId, int] = {}

    async def begin(self, user_id: UserId, sample_rate: int) -> None:
        """Start collecting a phrase.

        Args:
            user_id: Owner of the board that is streaming.
            sample_rate: Samples per second the board streams with.

        Returns:
            None.
        """
        self._chunks[user_id] = bytearray()
        self._rates[user_id] = sample_rate

    async def feed(self, user_id: UserId, samples: bytes) -> None:
        """Accept the next piece of a phrase.

        Args:
            user_id: Owner of the board that is streaming.
            samples: Raw samples of the piece.

        Returns:
            None.
        """
        buffer = self._chunks.setdefault(user_id, bytearray())
        if len(buffer) >= self._budget:
            return
        buffer.extend(samples)

    async def finish(self, user_id: UserId, reason: str) -> Transcript | None:
        """Close the phrase and return what was heard.

        Args:
            user_id: Owner of the board that was streaming.
            reason: Why the board stopped.

        Returns:
            Transcript | None: What was heard, or None when the phrase carried
            nothing usable.
        """
        buffer = self._chunks.pop(user_id, None)
        sample_rate = self._rates.pop(user_id, DEFAULT_SAMPLE_RATE)
        if not buffer:
            log.info("voice.phrase_without_samples", user=str(user_id), reason=reason)
            return None
        clip = AudioClip(samples=bytes(buffer), sample_rate=sample_rate)
        try:
            transcript = await self._recognizer.transcribe(clip)
        except VoiceUnavailableError as unavailable:
            log.warning(
                "voice.phrase_not_recognized",
                user=str(user_id),
                reason=unavailable.args[0] if unavailable.args else "unknown",
            )
            return None
        if not transcript.text.strip():
            return None
        return transcript
