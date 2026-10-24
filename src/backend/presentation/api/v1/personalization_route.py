"""Маршруты персональной проекции: настроек интерфейса и раскладки экрана.

Маршруты только переводят тела интерфейса в команды приложения. Значения по
умолчанию и правило «виджет указывает только на своё устройство» решают сценарии
прикладного слоя и агрегаты дома, здесь их не повторяют.
"""

from __future__ import annotations

from dishka import FromDishka
from dishka.integrations.fastapi import DishkaRoute
from fastapi import APIRouter

from backend.application.use_cases.personalization.read_dashboard import ReadDashboardUseCase
from backend.application.use_cases.personalization.read_preferences import ReadPreferencesUseCase
from backend.application.use_cases.personalization.update_dashboard import UpdateDashboardUseCase
from backend.application.use_cases.personalization.update_preferences import (
    UpdatePreferencesUseCase,
)
from backend.presentation.api.requests.personalization import (
    DashboardBody,
    PreferencesBody,
    dashboard_patch,
    preferences_patch,
)
from backend.presentation.api.responses.personalization import (
    DashboardResponse,
    PreferencesResponse,
    dashboard_of,
    preferences_of,
)
from backend.presentation.security_helpers import CurrentUserId

router = APIRouter(route_class=DishkaRoute, tags=["personalization"])


@router.get("/preferences", response_model=PreferencesResponse)
async def read_preferences(
    user_id: CurrentUserId,
    use_case: FromDishka[ReadPreferencesUseCase],
) -> PreferencesResponse:
    """Возвращает настройки интерфейса вошедшего аккаунта.

    Args:
        user_id: Владелец настроек, разрешённый из bearer-токена.
        use_case: Чтение настроек интерфейса.

    Returns:
        PreferencesResponse: Настройки такие, какие сохранены.
    """
    return preferences_of(await use_case.execute(user_id))


@router.patch("/preferences", response_model=PreferencesResponse)
async def update_preferences(
    body: PreferencesBody,
    user_id: CurrentUserId,
    use_case: FromDishka[UpdatePreferencesUseCase],
) -> PreferencesResponse:
    """Применяет частичное изменение настроек интерфейса.

    Args:
        body: Поля, которые человек хочет изменить.
        user_id: Владелец настроек, разрешённый из bearer-токена.
        use_case: Изменение настроек интерфейса.

    Returns:
        PreferencesResponse: Настройки такими, какими они стали.
    """
    return preferences_of(await use_case.execute(user_id, preferences_patch(body)))


@router.get("/dashboard", response_model=DashboardResponse)
async def read_dashboard(
    user_id: CurrentUserId,
    use_case: FromDishka[ReadDashboardUseCase],
) -> DashboardResponse:
    """Возвращает раскладку главного экрана вошедшего аккаунта.

    Args:
        user_id: Владелец раскладки, разрешённый из bearer-токена.
        use_case: Чтение раскладки экрана.

    Returns:
        DashboardResponse: Виджеты в порядке вывода.
    """
    return dashboard_of(await use_case.execute(user_id))


@router.patch("/dashboard", response_model=DashboardResponse)
async def update_dashboard(
    body: DashboardBody,
    user_id: CurrentUserId,
    use_case: FromDishka[UpdateDashboardUseCase],
) -> DashboardResponse:
    """Заменяет раскладку главного экрана целиком.

    Args:
        body: Виджеты в новом порядке.
        user_id: Владелец раскладки, разрешённый из bearer-токена.
        use_case: Замена раскладки экрана.

    Returns:
        DashboardResponse: Сохранённая раскладка.
    """
    return dashboard_of(await use_case.execute(user_id, dashboard_patch(body)))
