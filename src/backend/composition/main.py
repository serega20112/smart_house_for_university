"""Точка входа процесса интерфейса: uvicorn над уже собранным приложением.

Конфигурация читается здесь, а собрать по ней приложение — работа соседнего модуля:
так у процесса ровно одна причина меняться на каждом шаге, и его можно запустить
одной командой ``python -m backend.composition.main``.
"""

from __future__ import annotations

import uvicorn

from backend.composition.app import build_api_app
from backend.config import Settings


def main() -> None:
    """Запускает HTTP-сервер с приложением интерфейса."""
    settings = Settings()
    uvicorn.run(
        build_api_app(settings),
        host=settings.app_host,
        port=settings.app_port,
        log_level=settings.app_log_level.lower(),
    )


if __name__ == "__main__":
    main()
