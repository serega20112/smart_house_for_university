"""Voice command routes.

Three ways in, one pipeline out:

* ``POST /api/voice/text`` runs the pipeline on text, which is how the neural
  understanding is debugged without any hardware;
* ``POST /api/voice/audio`` runs it on raw samples, which is how a browser
  microphone or a recording is checked;
* ``POST /api/voice/mic`` opens the recording window of the board.

The board itself needs no route: it streams over its own WebSocket and the
command is executed for the account that board is paired with.
"""

from __future__ import annotations

import struct

from fastapi import APIRouter, HTTPException, Query, Request, Response, status

from backend.application.services import VoiceOutcome
from backend.presentation.api.messages import (
    voice_armed_message,
    voice_board_offline_message,
    voice_disarmed_message,
    voice_status_message,
)
from backend.presentation.api.requests import VoiceTextBody
from backend.presentation.api.responses import OperationResponse, VoiceResponse
from backend.presentation.api.security import AppContainer, CurrentUserId

router = APIRouter(prefix="/voice", tags=["voice"])

MAX_UPLOAD_BYTES = 1_500_000


@router.post("/text")
async def run_voice_text(
    body: VoiceTextBody, container: AppContainer, user_id: CurrentUserId
) -> VoiceResponse:
    """Execute a command as if it had been spoken.

    Args:
        body: Recognized text.
        container: Assembled dependency graph.
        user_id: Owner resolved from the bearer token.

    Returns:
        VoiceResponse: Transcript, reply and the result of the command.
    """
    outcome = await container.voice_router.execute_text(user_id, body.text)
    return VoiceResponse.from_outcome(outcome)


@router.post("/audio")
async def run_voice_audio(
    request: Request,
    container: AppContainer,
    user_id: CurrentUserId,
    sample_rate: int = Query(default=16000, ge=8000, le=48000),
) -> VoiceResponse:
    """Recognize and execute raw samples.

    The body is signed 16 bit little endian PCM without a header, exactly what a
    board streams, so the endpoint is exercised with the very bytes the hardware
    produces.

    Args:
        request: Incoming request carrying the samples.
        container: Assembled dependency graph.
        user_id: Owner resolved from the bearer token.
        sample_rate: Samples per second of the samples.

    Returns:
        VoiceResponse: Transcript, reply and the result of the command.

    Raises:
        HTTPException: When the upload is larger than a phrase may be.
    """
    pcm = await request.body()
    if len(pcm) > MAX_UPLOAD_BYTES:
        raise HTTPException(
            status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, "Слишком длинная запись"
        )
    outcome = await container.voice_router.speak(user_id, pcm, sample_rate)
    return VoiceResponse.from_outcome(outcome)


@router.post("/mic")
async def arm_microphone(
    container: AppContainer, user_id: CurrentUserId
) -> OperationResponse:
    """Let the board of the current user stream the next phrase.

    Args:
        container: Assembled dependency graph.
        user_id: Owner resolved from the bearer token.

    Returns:
        OperationResponse: Result of the request.
    """
    if not container.settings.voice_active:
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, "Голосовое управление выключено")
    if not await container.voice_router.arm(user_id):
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, voice_board_offline_message())
    return OperationResponse(status="SUCCESS", message=voice_armed_message())


@router.delete("/mic")
async def disarm_microphone(
    container: AppContainer, user_id: CurrentUserId
) -> OperationResponse:
    """Stop the board of the current user from streaming audio.

    Args:
        container: Assembled dependency graph.
        user_id: Owner resolved from the bearer token.

    Returns:
        OperationResponse: Result of the request.
    """
    return OperationResponse(
        status="SUCCESS",
        message=voice_disarmed_message(),
        data={"stopped": await container.voice_router.disarm(user_id)},
    )


@router.get("/status")
async def voice_status(container: AppContainer, user_id: CurrentUserId) -> dict:
    """Return the configuration of the voice pipeline.

    Args:
        container: Assembled dependency graph.
        user_id: Owner resolved from the bearer token.

    Returns:
        dict: Configuration and board presence.
    """
    settings = container.settings
    online = container.esp_connection.is_online(user_id)
    return {
        "status": "SUCCESS",
        "active": container.voice_router.active,
        "continuous": settings.voice_continuous,
        "sample_rate": settings.voice_sample_rate,
        "max_audio_sec": settings.voice_max_audio_sec,
        "tts_enabled": settings.voice_tts_enabled,
        "esp_online": online,
        "message": voice_status_message(
            container.voice_router.active,
            settings.voice_continuous,
            settings.voice_sample_rate,
            settings.voice_max_audio_sec,
            online,
        ),
    }


@router.get("/audio", response_class=Response)
async def stream_last_reply(container: AppContainer, user_id: CurrentUserId) -> Response:
    """Return the audio of the last answer, when synthesis is enabled.

    The interface plays it directly instead of decoding base64 in JavaScript, and
    a browser can also speak it through the normal media stack.

    Args:
        container: Assembled dependency graph.
        user_id: Owner resolved from the bearer token.

    Returns:
        Response: WAV audio of the last answer.
    """
    outcome: VoiceOutcome | None = container.voice_router.last_reply(user_id)
    audio = None if outcome is None else outcome.audio
    if audio is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Нет аудио последнего ответа")
    return Response(
        content=_ensure_wav(audio),
        media_type="audio/wav",
        headers={"Cache-Control": "no-store"},
    )


def _ensure_wav(audio: bytes) -> bytes:
    """Return the audio in a WAV container.

    The service already answers with WAV; a raw stream is wrapped here so the
    browser always receives a playable file.

    Args:
        audio: Audio bytes as returned by the voice service.

    Returns:
        bytes: WAV container.
    """
    if audio[:4] == b"RIFF":
        return audio
    return _wrap_wav(audio, 16000)


def _wrap_wav(pcm: bytes, sample_rate: int, channels: int = 1) -> bytes:
    """Wrap raw samples into a WAV container.

    Args:
        pcm: Raw 16 bit little endian samples.
        sample_rate: Samples per second.
        channels: Number of channels.

    Returns:
        bytes: WAV file.
    """
    byte_rate = sample_rate * channels * 2
    header = b"RIFF" + struct.pack("<I", 36 + len(pcm)) + b"WAVEfmt "
    header += struct.pack("<IHHIIHH", 16, 1, channels, sample_rate, byte_rate, channels * 2, 16)
    header += b"data" + struct.pack("<I", len(pcm))
    return header + pcm