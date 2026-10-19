"""WebSocket endpoint feeding the interface in realtime.

Browsers cannot attach an authorization header to a WebSocket handshake, so the
token arrives as a query parameter. It is resolved with the very same token
service the REST API uses, and a connection without a valid one is closed before
it is ever accepted.
"""

from __future__ import annotations

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, status

from backend.domain.value_objects.identity import UserId
from backend.infrastructure.logging_config import get_logger
from backend.presentation.websocket.hub import WebSocketHub

log = get_logger("websocket.endpoint")

router = APIRouter()

TOKEN_PARAMETER = "token"


@router.websocket("/ws")
async def events(websocket: WebSocket) -> None:
    """Keep a client subscribed to its own events until it disconnects.

    Args:
        websocket: Client connection.

    Returns:
        None.
    """
    user_id = _resolve(websocket)
    if user_id is None:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return
    hub: WebSocketHub = websocket.app.state.hub
    await hub.connect(user_id, websocket)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        await hub.disconnect(user_id, websocket)
    except Exception as exc:
        log.warning("web client connection failed", extra={"ctx": {"error": str(exc)}})
        await hub.disconnect(user_id, websocket)


def _resolve(websocket: WebSocket) -> UserId | None:
    token = websocket.query_params.get(TOKEN_PARAMETER, "")
    tokens = websocket.app.state.container.tokens
    return tokens.resolve(token) if token else None
