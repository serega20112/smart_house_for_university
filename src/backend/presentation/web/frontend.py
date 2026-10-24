"""Статический веб-интерфейс умного дома.

Отдаёт собранный интерфейс из бэкенда, чтобы цельный продукт жил из одного
процесса и из одного источника. Неизвестные пути отдают оболочку приложения: именно
так работает клиентский маршрутизатор.

Где лежит сборка, сначала читается из окружения, а потом достраивается из раскладки
репозитория и из раскладки образа, поэтому один и тот же код запускается и из
рабочей копии, и из контейнера — без пересборки.
"""

from __future__ import annotations

import os
from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

INDEX_FILE = "index.html"
ASSETS_DIRECTORY = "assets"
FRONTEND_DIST_VARIABLE = "FRONTEND_DIST"

CANDIDATES: tuple[Path, ...] = (
    Path("/app/src/frontend/dist"),
    Path(__file__).resolve().parents[3] / "frontend" / "dist",
    Path(__file__).resolve().parents[3] / "static",
)


def resolve_dist() -> Path | None:
    """Возвращает каталог со собранным интерфейсом.

    Returns:
        Path | None: Каталог сборки либо None, если её нет.
    """
    configured = os.getenv(FRONTEND_DIST_VARIABLE)
    if configured:
        return Path(configured)
    for candidate in CANDIDATES:
        if (candidate / INDEX_FILE).is_file():
            return candidate
    return None


def mount_frontend(app: FastAPI, dist: Path | None = None) -> bool:
    """Раздаёт собранный интерфейс из корня приложения.

    Args:
        app: Приложение, к которому интерфейс подвязывают.
        dist: Каталог с собранным интерфейсом; если не указан — находится сам.

    Returns:
        bool: True, когда интерфейс найден и подключён.
    """
    directory = dist or resolve_dist()
    if directory is None or not (directory / INDEX_FILE).is_file():
        return False

    root = directory.resolve()
    app.mount(
        f"/{ASSETS_DIRECTORY}",
        StaticFiles(directory=root / ASSETS_DIRECTORY),
        name=ASSETS_DIRECTORY,
    )

    @app.get("/", include_in_schema=False)
    async def index() -> FileResponse:
        """Возвращает оболочку приложения.

        Returns:
            FileResponse: Собранный index.
        """
        return FileResponse(root / INDEX_FILE)

    @app.get("/{path:path}", include_in_schema=False)
    async def fallback(path: str) -> FileResponse:
        """Возвращает статический файл, если он есть, иначе — оболочку.

        Args:
            path: Запрошенный путь относительно корня интерфейса.

        Returns:
            FileResponse: Статический файл или оболочка приложения.
        """
        candidate = (root / path).resolve()
        if candidate.is_file() and candidate.is_relative_to(root):
            return FileResponse(candidate)
        return FileResponse(root / INDEX_FILE)

    return True
