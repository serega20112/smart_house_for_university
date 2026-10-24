"""WebSocket-ручка, которой интерфейс получает события в реальном времени.

Браузер не может повесить заголовок авторизации на handshake WebSocket, поэтому токен
приходит параметром строки запроса и разбирается тем же адаптером токенов, которым
пользуется REST API: соединение без годного токена закрывается до того, как принято.

Сам концентратор — инфраструктура; здесь только решение, кого пустить и когда сказать
концентратору о соединении.
"""

from __future__ import annotations

from dishka import FromDishka
from dishka.integrations.fastapi import inject
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, status

from backend.application.interfaces.services.security.session_token_issuer import (
    SessionTokenIssuer,
)
from backend.infrastructure.system.logging import get_logger
from backend.infrastructure.websockets.hub import WebSocketHub

log = get_logger("websockets.router")

router = APIRouter()

TOKEN_PARAMETER = "token"
POLICY_VIOLATION_CLOSE = status.WS_1008_POLICY_VIOLATION


@router.websocket("/ws")
@inject
async def events(
    websocket: WebSocket,
    hub: FromDishka[WebSocketHub],
    tokens: FromDishka[SessionTokenIssuer],
) -> None:
    """Держит клиента подписанным на его собственные события до отключения.

    Args:
        websocket: Соединение клиента.
        hub: Концентратор, которому это соединение принадлежит.
        tokens: Тот, кто разбирает предъявленный токен сессии.
    """
    user_id = tokens.resolve(websocket.query_params.get(TOKEN_PARAMETER, ""))
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
