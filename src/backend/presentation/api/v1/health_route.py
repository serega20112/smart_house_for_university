"""Маршрут проверки доступности."""

from __future__ import annotations

from dishka import FromDishka
from dishka.integrations.fastapi import DishkaRoute
from fastapi import APIRouter

from backend import __version__
from backend.config import Settings
from backend.presentation.api.responses.common import HealthResponse

router = APIRouter(route_class=DishkaRoute, tags=["system"])


@router.get("/health", response_model=HealthResponse)
async def health(settings: FromDishka[Settings]) -> HealthResponse:
    """Возвращает доступность сервиса.

    Args:
        settings: Конфигурация запущенного процесса.

    Returns:
        HealthResponse: Название, версия и признак жизни сервиса.
    """
    return HealthResponse(status="ok", name=settings.app_name, version=__version__)
