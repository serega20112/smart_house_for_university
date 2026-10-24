"""Сборка HTTP API.

Здесь маршруты первой версии складываются в один префикс `/api`. Публичной
остаётся только ручка доступа: именно она заводит сессию, от которой зависят
все остальные.
"""

from __future__ import annotations

from dishka.integrations.fastapi import DishkaRoute
from fastapi import APIRouter

from backend.presentation.api import v1

api_router = APIRouter(route_class=DishkaRoute)
api_router.include_router(v1.health_router)
api_router.include_router(v1.auth_router)
api_router.include_router(v1.state_router)
api_router.include_router(v1.devices_router)
api_router.include_router(v1.boards_router)
api_router.include_router(v1.networks_router)
api_router.include_router(v1.automation_router)
api_router.include_router(v1.scenarios_router)
api_router.include_router(v1.commands_router)
api_router.include_router(v1.personalization_router)

__all__ = ["api_router"]
