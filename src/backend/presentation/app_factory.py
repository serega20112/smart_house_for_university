"""Фабрика FastAPI-приложения.

Собирает приложение из контейнера зависимостей, маршрутов и раздачи интерфейса.
Жизнью подсистем процесса — соединением с платами, концентратором событий, ботом и
посевом индекса — ведёт `backend.events.lifecycle`: здесь их не запускают и не гасят.

Приложение ровно одно на все аккаунты. Здесь ничего не заводится отдельно для
человека: дом появляется в тот момент, когда человек регистрируется, потому что
именно регистрация создаёт его устройства, настройки и панель.
"""

from __future__ import annotations

from dishka.integrations.fastapi import setup_dishka
from fastapi import FastAPI

from backend import __version__
from backend.config import Settings
from backend.events.lifecycle import lifespan
from backend.infrastructure.di import build_dishka_container
from backend.infrastructure.system.logging import configure_logging
from backend.presentation.api import api_router
from backend.presentation.errors import install_error_handlers
from backend.presentation.messages import NotificationFactoryImpl
from backend.presentation.web.frontend import mount_frontend
from backend.presentation.websockets.router import router as websocket_router


def create_app(settings: Settings) -> FastAPI:
    """Собирает FastAPI-приложение.

    Args:
        settings: Конфигурация, из которой строится граф; её передаёт композиционный
            корень, а не читает окружение само модуль сборки.

    Returns:
        FastAPI: Собранное приложение.
    """
    configure_logging(settings.app_log_level)

    container = build_dishka_container(
        settings,
        notifications=NotificationFactoryImpl(),
    )

    app = FastAPI(title=settings.app_name, version=__version__)
    app.state.container = container

    setup_dishka(container=container, app=app)

    app.include_router(api_router, prefix="/api")
    app.include_router(websocket_router)
    install_error_handlers(app)
    mount_frontend(app)
    app.router.lifespan_context = lifespan

    return app
