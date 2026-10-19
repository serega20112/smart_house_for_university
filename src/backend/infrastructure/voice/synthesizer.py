"""Speech synthesis over HTTP.

Only the text of a phrase travels as JSON, because text is text. The answer
travels as the raw audio the service rendered, which is what the speaker of a
board has to play and what a browser has to hand to an audio element; wrapping
it in JSON and base64 would only make both ends undo the work.
"""

from __future__ import annotations

import httpx

from backend.application.ports.voice import SpeechSynthesizer, VoiceUnavailableError
from backend.infrastructure.logging import get_logger

log = get_logger("voice.synthesizer")

SPEAK_PATH = "/speak"

UNREACHABLE = "voice_service_unreachable"
FAILED = "voice_service_failed"
DISABLED = "voice_synthesis_disabled"


class HttpSpeechSynthesizer(SpeechSynthesizer):
    """Speaks a phrase with the service running on another machine.

    Args:
        client: Connection to the speech service.
        base_url: Address of the speech service.
        timeout_sec: Timeout of a single request in seconds.
        enabled: Whether synthesis is switched on at all.

    Returns:
        None.
    """

    def __init__(
        self,
        client: httpx.AsyncClient,
        base_url: str,
        timeout_sec: float,
        enabled: bool = True,
    ) -> None:
        """Initialize the client.

        Args:
            client: Connection to the speech service.
            base_url: Address of the speech service.
            timeout_sec: Timeout of a single request in seconds.
            enabled: Whether synthesis is switched on at all.

        Returns:
            None.
        """
        self._client = client
        self._base_url = base_url.rstrip("/")
        self._timeout = timeout_sec
        self._enabled = enabled

    async def synthesize(self, text: str) -> bytes:
        """Speak a phrase.

        Args:
            text: Phrase to speak.

        Returns:
            bytes: Audio of the phrase, empty when synthesis is switched off.

        Raises:
            VoiceUnavailableError: When the service cannot answer.
        """
        if not self._enabled:
            log.info("voice.synthesis_skipped")
            return b""
        try:
            response = await self._client.post(
                f"{self._base_url}{SPEAK_PATH}",
                json={"text": text},
                timeout=self._timeout,
            )
            response.raise_for_status()
        except httpx.HTTPStatusError as error:
            raise VoiceUnavailableError(FAILED) from error
        except httpx.HTTPError as error:
            raise VoiceUnavailableError(UNREACHABLE) from error
        return bytes(response.content)
