"""WebSocket-ручка, которой интерфейс получает события в реальном времени.

Браузер не может повесить заголовок авторизации на handshake WebSocket, поэтому соединение
приходит с коротким одноразовым билетом в параметре строки запроса: REST выдаёт его по
текущей сессии, а здесь билет один раз обменивается на аккаунт. Соединение без годного
билета закрывается до того, как принято; сам токен сессии в адресе не появляется, поэтому
утёкшая строка запроса не даёт доступа к дому.

Сам концентратор — инфраструктура; здесь только решение, кого пустить и когда сказать
концентратору о соединении.
"""

from __future__ import annotations

from dishka import FromDishka
from dishka.integrations.fastapi import inject
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, status

from backend.application.interfaces.services.security.realtime_ticket_store import (
    RealtimeTicketStore,
)
from backend.infrastructure.system.logging import get_logger
from backend.infrastructure.websockets.hub import WebSocketHub

log = get_logger("websockets.router")

router = APIRouter()

TICKET_PARAMETER = "ticket"
POLICY_VIOLATION_CLOSE = status.WS_1008_POLICY_VIOLATION


@router.websocket("/ws")
@inject
async def events(
    websocket: WebSocket,
    hub: FromDishka[WebSocketHub],
    tickets: FromDishka[RealtimeTicketStore],
) -> None:
    """Держит клиента подписанным на его собственные события до отключения.

    Args:
        websocket: Соединение клиента.
        hub: Концентратор, которому это соединение принадлежит.
        tickets: Тот, кто обменивает предъявленный билет на аккаунт.
    """
    user_id = await tickets.redeem(websocket.query_params.get(TICKET_PARAMETER, ""))
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
