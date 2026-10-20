"""Speech recognition over HTTP.

Audio travels as the raw samples it is: the body of the request is exactly the
bytes the board produced, and the sample rate travels in a header. Encoding them
into JSON as base64 would inflate a clip by a third and force both ends to agree
on a container format neither of them needs.
"""

from __future__ import annotations

import httpx

from smart_home.application.ports.voice import (
    AudioClip,
    SpeechRecognizer,
    Transcript,
    VoiceUnavailableError,
)
from smart_home.infrastructure.logging import get_logger

log = get_logger("voice.recognizer")

TRANSCRIBE_PATH = "/transcribe"
HEADER_SAMPLE_RATE = "X-Sample-Rate"
HEADER_FORMAT = "X-Audio-Format"
FORMAT_PCM_S16LE = "pcm_s16le"

UNREACHABLE = "voice_service_unreachable"
BAD_ANSWER = "voice_service_bad_answer"
FAILED = "voice_service_failed"
DISABLED = "voice_disabled"


class HttpSpeechRecognizer(SpeechRecognizer):
    """Recognizes speech with the service running on another machine.

    Args:
        client: Connection to the speech service.
        base_url: Address of the speech service.
        timeout_sec: Timeout of a single request in seconds.

    Returns:
        None.
    """

    def __init__(self, client: httpx.AsyncClient, base_url: str, timeout_sec: float) -> None:
        """Initialize the client.

        Args:
            client: Connection to the speech service.
            base_url: Address of the speech service.
            timeout_sec: Timeout of a single request in seconds.

        Returns:
            None.
        """
        self._client = client
        self._base_url = base_url.rstrip("/")
        self._timeout = timeout_sec

    async def transcribe(self, clip: AudioClip) -> Transcript:
        """Recognize speech in a clip.

        Args:
            clip: Audio of one phrase.

        Returns:
            Transcript: Recognized text.

        Raises:
            VoiceUnavailableError: When the service cannot answer.
        """
        try:
            response = await self._client.post(
                f"{self._base_url}{TRANSCRIBE_PATH}",
                content=clip.samples,
                headers={
                    HEADER_SAMPLE_RATE: str(clip.sample_rate),
                    HEADER_FORMAT: FORMAT_PCM_S16LE,
                    "Content-Type": "application/octet-stream",
                },
                timeout=self._timeout,
            )
            response.raise_for_status()
            payload = response.json()
        except httpx.HTTPStatusError as error:
            raise VoiceUnavailableError(FAILED) from error
        except httpx.HTTPError as error:
            raise VoiceUnavailableError(UNREACHABLE) from error
        except ValueError as error:
            raise VoiceUnavailableError(BAD_ANSWER) from error
        if not isinstance(payload, dict):
            raise VoiceUnavailableError(BAD_ANSWER)
        text = payload.get("text")
        if not isinstance(text, str):
            raise VoiceUnavailableError(BAD_ANSWER)
        return Transcript(text=text, confidence=_as_float(payload.get("confidence"), 1.0))


class UnavailableSpeechRecognizer(SpeechRecognizer):
    """Stands in for the recognizer while speech is switched off.

    Keeping one implementation of the port for the switched off case means the
    rest of the application never asks whether the pipeline is available: it asks
    and gets an honest answer.

    Args:
        reason: Machine readable reason reported to callers.

    Returns:
        None.
    """

    def __init__(self, reason: str = DISABLED) -> None:
        """Initialize the stub.

        Args:
            reason: Machine readable reason reported to callers.

        Returns:
            None.
        """
        self._reason = reason

    async def transcribe(self, clip: AudioClip) -> Transcript:
        """Report that recognition is unavailable.

        Args:
            clip: Audio of one phrase.

        Returns:
            Transcript: Never returned.

        Raises:
            VoiceUnavailableError: Always.
        """
        raise VoiceUnavailableError(self._reason)


def _as_float(value: object, default: float) -> float:
    if isinstance(value, bool) or not isinstance(value, int | float):
        return default
    return float(value)
