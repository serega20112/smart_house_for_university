"""Voice routes and their isolation.

The point of these tests is that a spoken phrase is bound to the session that
produced it, exactly like a typed command, and that the routes stay honest when
the models are switched off.
"""

from __future__ import annotations

from collections.abc import AsyncIterator

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from smart_home_backend.application.interface.services import (
    AudioClip,
    SpeechRecognizer,
    Transcript,
)
from smart_home_backend.config import Settings
from smart_home_backend.infrastructure.database import create_schema
from smart_home_backend.infrastructure.di import build_container
from smart_home_backend.presentation.app_factory import create_app
from smart_home_backend.presentation.voice_composer import CommandReplyComposer


class EchoRecognizer(SpeechRecognizer):
    """Recognizer answering with a fixed phrase."""

    def __init__(self, text: str) -> None:
        """Initialize the stub.

        Args:
            text: Text the recognizer reports.

        Returns:
            None.
        """
        self.text = text
        self.calls = 0

    async def transcribe(self, clip: AudioClip) -> Transcript:
        """Report the prepared transcript.

        Args:
            clip: Audio of the phrase.

        Returns:
            Transcript: Prepared transcript.
        """
        self.calls += 1
        return Transcript(text=self.text)


@pytest_asyncio.fixture
async def voice_client(settings: Settings, events, board) -> AsyncIterator[AsyncClient]:
    settings.voice_enabled = True
    settings.voice_base_url = "http://127.0.0.1:9"
    settings.voice_tts_enabled = False
    settings.voice_continuous = False
    container = build_container(settings, events, CommandReplyComposer())
    await create_schema(container.engine)
    app = create_app(settings)
    app.state.container = container
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as instance:
        instance.container = container  # type: ignore[attr-defined]
        yield instance
    await container.engine.dispose()


async def register(client: AsyncClient, email: str, name: str) -> dict:
    response = await client.post(
        "/api/auth/register",
        json={"email": email, "password": "super-secret-1", "display_name": name},
    )
    assert response.status_code == 201, response.text
    return response.json()


def auth(session: dict) -> dict:
    return {"Authorization": f"Bearer {session['access_token']}"}


async def test_text_phrase_is_executed_like_a_typed_command(voice_client: AsyncClient) -> None:
    session = await register(voice_client, "voice@example.com", "Вася")
    response = await voice_client.post(
        "/api/voice/text",
        json={"text": "включи свет"},
        headers=auth(session),
    )

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["transcript"] == "включи свет"
    assert body["status"] in {"SUCCESS", "INVALID_INPUT", "NOT_FOUND", "UNSUPPORTED"}
    assert body["message"]


async def test_audio_is_recognized_and_executed(
    voice_client: AsyncClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    session = await register(voice_client, "audio@example.com", "Вася")
    recognizer = EchoRecognizer("какая температура")
    monkeypatch.setattr(voice_client.container.voice_engine, "transcribe", recognizer.transcribe)

    response = await voice_client.post(
        "/api/voice/audio?sample_rate=16000",
        content=bytes(8000),
        headers={**auth(session), "Content-Type": "application/octet-stream"},
    )

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["transcript"] == "какая температура"
    assert recognizer.calls == 1


async def test_empty_audio_is_not_pushed_into_the_models(
    voice_client: AsyncClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    session = await register(voice_client, "empty@example.com", "Вася")
    recognizer = EchoRecognizer("что-то")
    monkeypatch.setattr(voice_client.container.voice_engine, "transcribe", recognizer.transcribe)

    response = await voice_client.post("/api/voice/audio", content=b"", headers=auth(session))

    assert response.status_code == 200
    assert response.json()["status"] == "NO_SPEECH"
    assert recognizer.calls == 0


@pytest_asyncio.fixture
async def plain_client(settings: Settings, events, board) -> AsyncIterator[AsyncClient]:
    container = build_container(settings, events, CommandReplyComposer())
    await create_schema(container.engine)
    app = create_app(settings)
    app.state.container = container
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as instance:
        instance.container = container  # type: ignore[attr-defined]
        yield instance
    await container.engine.dispose()


async def test_voice_requires_a_session(plain_client: AsyncClient) -> None:
    response = await plain_client.post("/api/voice/text", json={"text": "включи свет"})
    assert response.status_code == 401


async def test_status_reports_the_configured_pipeline(voice_client: AsyncClient) -> None:
    session = await register(voice_client, "status@example.com", "Вася")
    response = await voice_client.get("/api/voice/status", headers=auth(session))

    assert response.status_code == 200
    body = response.json()
    assert body["active"] is True
    assert body["sample_rate"] == 8000


async def test_arming_fails_without_a_board(voice_client: AsyncClient) -> None:
    session = await register(voice_client, "arm@example.com", "Вася")
    response = await voice_client.post("/api/voice/mic", headers=auth(session))

    assert response.status_code == 503