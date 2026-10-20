"""WebSocket endpoint feeding the interface in realtime.

Browsers cannot attach an authorization header to a WebSocket handshake, so the
token arrives as a query parameter. It is resolved with the very same token
service the REST API uses, and a connection without a valid one is closed before
it is ever accepted.
"""

from __future__ import annotations

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, status

from smart_home.application.ports.services import SessionTokenIssuer
from smart_home.domain.identifiers import UserId
from smart_home.infrastructure.logging import get_logger
from smart_home.presentation.websocket.hub import WebSocketHub

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
    tokens: SessionTokenIssuer = websocket.app.state.tokens
    hub: WebSocketHub = websocket.app.state.hub
    user_id = _resolve(websocket, tokens)
    if user_id is None:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return
    await hub.connect(user_id, websocket)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        await hub.disconnect(user_id, websocket)
    except Exception as exc:
        log.warning("web client connection failed", extra={"ctx": {"error": str(exc)}})
        await hub.disconnect(user_id, websocket)


def _resolve(websocket: WebSocket, tokens: SessionTokenIssuer) -> UserId | None:
    token = websocket.query_params.get(TOKEN_PARAMETER, "")
    return tokens.resolve(token) if token else None
