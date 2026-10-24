"""Версия HTTP API, которую обслуживает эта сборка.

Каждый маршрут — один файл и одна тема: устройства, платы, их сеть, сценарии,
автоматизация, состояние дома, свободная команда, персональная проекция, аккаунт
и доступность сервиса.
"""

from backend.presentation.api.v1.auth_route import router as auth_router
from backend.presentation.api.v1.automation_route import router as automation_router
from backend.presentation.api.v1.boards_route import router as boards_router
from backend.presentation.api.v1.commands_route import router as commands_router
from backend.presentation.api.v1.devices_route import router as devices_router
from backend.presentation.api.v1.health_route import router as health_router
from backend.presentation.api.v1.networks_route import router as networks_router
from backend.presentation.api.v1.personalization_route import router as personalization_router
from backend.presentation.api.v1.scenarios_route import router as scenarios_router
from backend.presentation.api.v1.state_route import router as state_router

__all__ = [
    "auth_router",
    "automation_router",
    "boards_router",
    "commands_router",
    "devices_router",
    "health_router",
    "networks_router",
    "personalization_router",
    "scenarios_router",
    "state_router",
]
