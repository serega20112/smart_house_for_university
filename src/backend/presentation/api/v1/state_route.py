"""Маршрут состояния дома.

Главный экран интерфейса показывает весь дом сразу, и ручка отдаёт его одним
куском. Части приходят из сохранённой настройки и из живого состояния аккаунта, а
собирает их один сценарий приложения, поэтому числа на экране принадлежат
достаточно близким моментам, чтобы им можно было верить.
"""

from __future__ import annotations

from dishka import FromDishka
from dishka.integrations.fastapi import DishkaRoute
from fastapi import APIRouter

from backend.application.use_cases.home.read_home_snapshot import ReadHomeSnapshotUseCase
from backend.presentation.api.responses.home import HomeStateResponse, snapshot_of
from backend.presentation.security_helpers import CurrentUserId

router = APIRouter(route_class=DishkaRoute, tags=["state"])


@router.get("/state", response_model=HomeStateResponse)
async def home_state(
    user_id: CurrentUserId, use_case: FromDishka[ReadHomeSnapshotUseCase]
) -> HomeStateResponse:
    """Возвращает полный снимок главного экрана.

    Args:
        user_id: Владелец, разрешённый из bearer-токена.
        use_case: Чтение дома одного аккаунта.

    Returns:
        HomeStateResponse: Снимок дома текущего аккаунта.
    """
    return snapshot_of(await use_case.execute(user_id))
