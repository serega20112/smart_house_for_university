"""WebSocket endpoint feeding the interface in realtime."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from smart_home_backend.infrastructure.logging_config import get_logger
from smart_home_backend.presentation.websocket.hub import WebSocketHub

log = get_logger("websocket.endpoint")

router = APIRouter()


@router.websocket("/ws")
async def events(websocket: WebSocket) -> None:
    """Keep a client subscribed until it disconnects.

    Args:
        websocket: Client connection.

    Returns:
        None.
    """
    hub: WebSocketHub = websocket.app.state.hub
    await hub.connect(websocket)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        await hub.disconnect(websocket)
    except Exception as exc:
        log.warning("web client connection failed", extra={"ctx": {"error": str(exc)}})
        await hub.disconnect(websocket)
