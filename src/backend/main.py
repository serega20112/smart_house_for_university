"""Точка входа бэкенда.

Запускает uvicorn с собранным приложением. Соединение с платами, фоновые циклы и бот
Telegram живут внутри времени жизни приложения.
"""

from __future__ import annotations

import uvicorn

from backend.config import Settings
from backend.presentation.app_factory import create_app


def main() -> None:
    """Запускает HTTP-сервер."""
    settings = Settings()
    uvicorn.run(
        create_app(settings),
        host=settings.app_host,
        port=settings.app_port,
        log_level=settings.app_log_level.lower(),
    )


if __name__ == "__main__":
    main()
