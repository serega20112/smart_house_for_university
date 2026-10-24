"""Фабрика FastAPI-приложения.

Собирает приложение из готового графа зависимостей, маршрутов и раздачи
интерфейса. Контейнер и жизненный цикл приходят аргументами: их выбирает
композиция процесса, а слой интерфейса не решает, с чем процесс стартует, и не
ищет чужие объекты в состоянии приложения.

Приложение ровно одно на все аккаунты. Здесь ничего не заводится отдельно для
человека: дом появляется в тот момент, когда человек регистрируется, потому что
именно регистрация создаёт его устройства, настройки и панель.
"""

from __future__ import annotations

from collections.abc import Callable
from contextlib import AbstractAsyncContextManager

from dishka import AsyncContainer
from dishka.integrations.fastapi import setup_dishka
from fastapi import FastAPI

from backend import __version__
from backend.config import Settings
from backend.presentation.api import api_router
from backend.presentation.errors import install_error_handlers
from backend.presentation.web.frontend import mount_frontend
from backend.presentation.websockets.router import router as websocket_router

AppLifespan = Callable[[FastAPI], AbstractAsyncContextManager[None]]


def create_app(
    settings: Settings,
    container: AsyncContainer,
    lifespan: AppLifespan,
) -> FastAPI:
    """Собирает FastAPI-приложение.

    Args:
        settings: Конфигурация, которую процесс получил от композиции.
        container: Собранный граф зависимостей этого процесса.
        lifespan: Жизненный цикл, который FastAPI откроет на старте и закроет на
            остановке.

    Returns:
        FastAPI: Собранное приложение.
    """
    app = FastAPI(title=settings.app_name, version=__version__)
    setup_dishka(container=container, app=app)

    app.include_router(api_router, prefix="/api")
    app.include_router(websocket_router)
    install_error_handlers(app)
    mount_frontend(app, settings.frontend_dist)
    app.router.lifespan_context = lifespan

    return app
