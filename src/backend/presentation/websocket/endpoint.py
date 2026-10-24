"""WebSocket-ручка, которой интерфейс получает события в реальном времени.

Браузер не может повесить заголовок авторизации на handshake WebSocket, поэтому
токен приходит параметром строки запроса и разбирается тем же сервисом токенов,
которым пользуется REST API: соединение без годного токена закрывается до того,
как оно принято.
"""

from __future__ import annotations

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, status

from backend.infrastructure.logging import get_logger
from backend.presentation.dependencies import hub_of, tokens_of

log = get_logger("websocket.endpoint")

router = APIRouter()

TOKEN_PARAMETER = "token"
POLICY_VIOLATION_CLOSE = status.WS_1008_POLICY_VIOLATION


@router.websocket("/ws")
async def events(websocket: WebSocket) -> None:
    """Держит клиента подписанным на его собственные события до отключения.

    Args:
        websocket: Соединение клиента.
    """
    hub = hub_of(websocket.app)
    user_id = tokens_of(websocket.app).resolve(websocket.query_params.get(TOKEN_PARAMETER, ""))
    if user_id is None:
        await websocket.close(code=POLICY_VIOLATION_CLOSE)
        return
    await hub.connect(user_id, websocket)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        await hub.disconnect(user_id, websocket)
    except Exception as error:
        log.warning("websocket.client_failed", user=str(user_id), error=str(error))
        await hub.disconnect(user_id, websocket)
