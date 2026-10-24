"""Маршруты автоматизации.

Автоматизация — та часть системы, что действует сама, поэтому интерфейс показывает
её настройку и меняет её. Достижима ли цель — вопрос домена, и домен отвечает на
него отказом от изменения.
"""

from __future__ import annotations

from dishka import FromDishka
from dishka.integrations.fastapi import DishkaRoute
from fastapi import APIRouter

from backend.application.interfaces.queries.automation_queries import AutomationQueries
from backend.application.use_cases.automation.update_automation import UpdateAutomationUseCase
from backend.presentation.api.requests.automation import AutomationUpdateBody, patch_of
from backend.presentation.api.responses.automation import AutomationResponse, automation_of
from backend.presentation.security_helpers import CurrentUserId

router = APIRouter(route_class=DishkaRoute, prefix="/automation", tags=["automation"])


@router.get("", response_model=AutomationResponse)
async def read_automation(
    user_id: CurrentUserId, queries: FromDishka[AutomationQueries]
) -> AutomationResponse:
    """Возвращает настройку автоматизации текущего аккаунта.

    Args:
        user_id: Владелец, разрешённый из bearer-токена.
        queries: Чтения настройки автоматизации.

    Returns:
        AutomationResponse: Настройка аккаунта.
    """
    return automation_of(await queries.get(user_id))


@router.put("", response_model=AutomationResponse)
async def update_automation(
    body: AutomationUpdateBody,
    user_id: CurrentUserId,
    use_case: FromDishka[UpdateAutomationUseCase],
) -> AutomationResponse:
    """Применяет частичное изменение настройки автоматизации.

    Args:
        body: Поля, которые нужно изменить.
        user_id: Владелец, разрешённый из bearer-токена.
        use_case: Изменение настройки.

    Returns:
        AutomationResponse: Настройка такой, какой она стала.
    """
    automation = await use_case.execute(user_id, patch_of(body))
    return automation_of(automation)
