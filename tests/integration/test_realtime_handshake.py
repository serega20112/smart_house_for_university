"""Интерфейс открывает WebSocket по одноразовому билету, а не по токену сессии.

Это сквозная проверка 5.5.1 по-настоящему: приложение принимает соединение, если REST
выдал билет под текущей сессией, и отвергает повторный обмен того же билета. Тест идёт к
живым PostgreSQL и Redis (иначе пропускается), потому что билет живёт в Redis, а владелец
берётся из базы — подменить их нечем.
"""

from __future__ import annotations

import asyncio
from uuid import uuid4

import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine
from starlette.testclient import TestClient
from starlette.websockets import WebSocketDisconnect

from backend.config.settings import Settings
from backend.presentation.app_factory import create_app


def _provision(client: TestClient) -> tuple[str, str]:
    """Регистрирует уникальный аккаунт и возвращает его токен и идентификатор.

    Args:
        client: Запущенное приложение с поднятым lifespan.

    Returns:
        tuple[str, str]: Bearer-токен сессии и идентификатор нового аккаунта.
    """
    email = f"ticket-{uuid4().hex}@example.com"
    response = client.post(
        "/api/auth/register",
        json={"email": email, "password": "secret-pass-1", "display_name": "Ticket Probe"},
    )
    assert response.status_code == 201, response.text
    document = response.json()
    return document["access_token"], document["user"]["id"]


def test_realtime_opens_with_a_ticket_and_refuses_its_reuse() -> None:
    """Билет открывает соединение ровно один раз: второй обмен уже не годится."""
    settings = Settings()

    async def _probe() -> None:
        engine = create_async_engine(settings.database_url)
        try:
            async with engine.connect() as connection:
                await connection.execute(text("SELECT 1 FROM users LIMIT 0"))
        finally:
            await engine.dispose()

    try:
        asyncio.run(_probe())
    except Exception as error:
        pytest.skip(f"PostgreSQL not reachable for realtime handshake test: {error}")

    application = create_app(settings)
    user_id = ""
    with TestClient(application) as client:
        token, user_id = _provision(client)

        issued = client.post(
            "/api/auth/realtime-ticket", headers={"Authorization": f"Bearer {token}"}
        )
        assert issued.status_code == 200, issued.text
        ticket = issued.json()["ticket"]
        assert ticket

        connect_url = f"/ws?ticket={ticket}"
        with client.websocket_connect(connect_url) as socket:
            socket.send_text("hello")

        with (
            pytest.raises(WebSocketDisconnect),
            client.websocket_connect(connect_url) as reused,
        ):
            reused.send_text("hello")

    async def _cleanup() -> None:
        engine = create_async_engine(settings.database_url)
        try:
            async with engine.begin() as connection:
                await connection.execute(text("DELETE FROM users WHERE id = :id"), {"id": user_id})
        finally:
            await engine.dispose()

    if user_id:
        asyncio.run(_cleanup())
