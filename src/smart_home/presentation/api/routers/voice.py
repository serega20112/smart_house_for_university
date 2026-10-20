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

import base64
import struct

from dishka import FromDishka
from dishka.integrations.fastapi import DishkaRoute
from fastapi import APIRouter, HTTPException, Query, Request, Response, status

from smart_home.application.dto import BoardView, UserId
from smart_home.application.ports.boards import BoardGateway
from smart_home.application.ports.queries.boards import BoardQueries
from smart_home.application.ports.voice import VoiceUnavailableError
from smart_home.application.services.voice_service import VoiceCommandService, VoiceReply
from smart_home.config import Settings
from smart_home.presentation.api.messages import (
    VOICE_ARMED_MESSAGE,
    VOICE_BOARD_OFFLINE,
    VOICE_DISABLED,
    VOICE_DISARMED_MESSAGE,
    VOICE_NOT_CONFIGURED,
    VOICE_STATUS_MESSAGE,
)
from smart_home.presentation.api.schemas import (
    OperationResponse,
    VoiceResponse,
    VoiceStatusResponse,
    VoiceTextBody,
)
from smart_home.presentation.api.security import CurrentUserId

router = APIRouter(route_class=DishkaRoute, prefix="/voice", tags=["voice"])

MAX_UPLOAD_BYTES = 1_500_000


@router.post("/text", response_model=VoiceResponse)
async def run_voice_text(
    body: VoiceTextBody,
    user_id: CurrentUserId,
    voice: FromDishka[VoiceCommandService],
) -> VoiceResponse:
    """Execute a command as if it had been spoken.

    Args:
        body: Recognized text.
        user_id: Owner resolved from the bearer token.
        voice: Voice pipeline of the account.

    Returns:
        VoiceResponse: Transcript, reply and the result of the command.
    """
    return _response_of(await voice.run_text(user_id, body.text))


@router.post("/audio", response_model=VoiceResponse)
async def run_voice_audio(
    request: Request,
    user_id: CurrentUserId,
    voice: FromDishka[VoiceCommandService],
    sample_rate: int = Query(default=16000, ge=8000, le=48000),
) -> VoiceResponse:
    """Recognize and execute raw samples.

    The body is signed 16 bit little endian PCM without a header, exactly what a
    board streams, so the endpoint is exercised with the very bytes the hardware
    produces.

    Args:
        request: Incoming request carrying the samples.
        user_id: Owner resolved from the bearer token.
        voice: Voice pipeline of the account.
        sample_rate: Samples per second of the samples.

    Returns:
        VoiceResponse: Transcript, reply and the result of the command.

    Raises:
        HTTPException: When the upload is larger than a phrase may be or speech
            recognition is unavailable.
    """
    del sample_rate
    pcm = await request.body()
    if len(pcm) > MAX_UPLOAD_BYTES:
        raise HTTPException(status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, "Слишком длинная запись.")
    try:
        reply = await voice.run_clip(user_id, pcm)
    except VoiceUnavailableError as exc:
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, str(exc)) from exc
    return _response_of(reply)


@router.post("/mic", response_model=OperationResponse)
async def arm_microphone(
    user_id: CurrentUserId,
    voice: FromDishka[VoiceCommandService],
    settings: FromDishka[Settings],
    queries: FromDishka[BoardQueries],
    gateway: FromDishka[BoardGateway],
) -> OperationResponse:
    """Let the board of the current user stream the next phrase.

    Args:
        user_id: Owner resolved from the bearer token.
        voice: Voice pipeline of the account.
        settings: Configuration of the deployment.
        queries: Reads of the boards.
        gateway: Live transport, asked whether a board is connected.

    Returns:
        OperationResponse: Result of the request.

    Raises:
        HTTPException: When voice is switched off on the server or no board of the
            account is connected.
    """
    if not settings.voice.active:
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, VOICE_DISABLED)
    board = await _board_of(user_id, queries, gateway)
    if board is None:
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, VOICE_BOARD_OFFLINE)
    if not await voice.arm(user_id, board.id):
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, VOICE_BOARD_OFFLINE)
    return OperationResponse(status="SUCCESS", message=VOICE_ARMED_MESSAGE)


@router.delete("/mic", response_model=OperationResponse)
async def disarm_microphone(
    user_id: CurrentUserId,
    voice: FromDishka[VoiceCommandService],
    queries: FromDishka[BoardQueries],
    gateway: FromDishka[BoardGateway],
) -> OperationResponse:
    """Stop the board of the current user from streaming audio.

    Args:
        user_id: Owner resolved from the bearer token.
        voice: Voice pipeline of the account.
        queries: Reads of the boards.
        gateway: Live transport, asked whether a board is connected.

    Returns:
        OperationResponse: Result of the request.
    """
    board = await _board_of(user_id, queries, gateway)
    if board is not None:
        await voice.disarm(user_id, board.id)
    return OperationResponse(status="SUCCESS", message=VOICE_DISARMED_MESSAGE)


@router.get("/status", response_model=VoiceStatusResponse)
async def voice_status(
    user_id: CurrentUserId,
    voice: FromDishka[VoiceCommandService],
    settings: FromDishka[Settings],
    queries: FromDishka[BoardQueries],
    gateway: FromDishka[BoardGateway],
) -> VoiceStatusResponse:
    """Return the configuration of the voice pipeline.

    Args:
        user_id: Owner resolved from the bearer token.
        voice: Voice pipeline of the account.
        settings: Configuration of the deployment.
        queries: Reads of the boards.
        gateway: Live transport, asked whether a board is connected.

    Returns:
        VoiceStatusResponse: Configuration and board presence.
    """
    online = await _board_of(user_id, queries, gateway) is not None
    active = settings.voice.active
    return VoiceStatusResponse(
        active=active,
        sample_rate=voice.sample_rate,
        max_audio_sec=settings.voice.max_audio_sec,
        board_online=online,
        message=_status_message(active, online),
    )


@router.get("/audio", response_class=Response, response_model=None)
async def stream_last_reply(
    user_id: CurrentUserId, voice: FromDishka[VoiceCommandService]
) -> Response:
    """Return the audio of the last answer, when synthesis is enabled.

    The interface plays it directly instead of decoding base64 in JavaScript, and
    a browser can also speak it through the normal media stack.

    Args:
        user_id: Owner resolved from the bearer token.
        voice: Voice pipeline of the account.

    Returns:
        Response: WAV audio of the last answer.

    Raises:
        HTTPException: When there is nothing to play.
    """
    audio = await voice.last_audio(user_id)
    if not audio:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Нет ответа для воспроизведения.")
    return Response(
        content=_ensure_wav(audio),
        media_type="audio/wav",
        headers={"Cache-Control": "no-store"},
    )


async def _board_of(
    user_id: UserId, queries: BoardQueries, gateway: BoardGateway
) -> BoardView | None:
    """Return a board of the account that can take a microphone request.

    Args:
        user_id: Owner of the boards.
        queries: Reads of the boards.
        gateway: Live transport, asked whether a board is connected.

    Returns:
        BoardView | None: A connected board, or the first board of the account,
        or None when the account owns no board.
    """
    boards = await queries.list_for(user_id)
    for board in boards:
        if gateway.is_connected(user_id, board.id):
            return board
    return boards[0] if boards else None


def _status_message(active: bool, online: bool) -> str:
    """Return the sentence describing the voice pipeline.

    Args:
        active: Whether speech recognition is configured on the server.
        online: Whether a board of the account is connected.

    Returns:
        str: Text shown to the person.
    """
    if not active:
        return VOICE_NOT_CONFIGURED
    if not online:
        return VOICE_BOARD_OFFLINE
    return VOICE_STATUS_MESSAGE


def _response_of(reply: VoiceReply) -> VoiceResponse:
    """Return the body of a voice answer.

    Args:
        reply: What the voice pipeline produced.

    Returns:
        VoiceResponse: Body of the answer.
    """
    return VoiceResponse(
        status="SUCCESS",
        transcript=reply.transcript,
        answer=reply.answer,
        audio_base64=(base64.b64encode(reply.audio).decode("ascii") if reply.audio else None),
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
