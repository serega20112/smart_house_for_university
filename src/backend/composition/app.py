"""Сборка приложения интерфейса: конфигурация, граф, маршруты и жизненный цикл.

Один вызов этой функции — это весь процесс интерфейса: он решает, с какой
конфигурацией жить, собирает граф для роли API, берёт жизненный цикл над этим
графом и отдаёт всё фабрике приложения. Ни один слой ниже не делает этого сам.
"""

from __future__ import annotations

from fastapi import FastAPI

from backend.composition.lifecycle import lifespan_of
from backend.config.settings import Settings
from backend.infrastructure.di import ProcessRole, build_dishka_container
from backend.infrastructure.system.logging import configure_logging
from backend.presentation.app_factory import create_app
from backend.presentation.messages import NotificationFactoryImpl


def build_api_app(settings: Settings) -> FastAPI:
    """Собирает приложение интерфейса вместе с его графом зависимостей.

    Args:
        settings: Конфигурация развёртывания.

    Returns:
        FastAPI: Готовое приложение, которому осталось только слушать порт.
    """
    configure_logging(settings.app_log_level)
    container = build_dishka_container(
        settings,
        notifications=NotificationFactoryImpl(),
        role=ProcessRole.API,
    )
    return create_app(settings, container, lifespan_of(container))
