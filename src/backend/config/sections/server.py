"""HTTP-сервер, логирование и доступ браузера."""

from __future__ import annotations

import os

from backend.config.sections.parsing import as_list


def app_name() -> str:
    """Имя, которое отдаёт проба доступности.

    Returns:
        str: Имя развёртывания.
    """
    return os.getenv("APP_NAME", "smart-home-backend")


def app_host() -> str:
    """Адрес, на котором слушает HTTP-сервер.

    Returns:
        str: Адрес привязки.
    """
    return os.getenv("APP_HOST", "0.0.0.0")


def app_port() -> int:
    """Порт HTTP-сервера.

    Returns:
        int: Порт прослушивания.
    """
    return int(os.getenv("APP_PORT", "8000"))


def app_log_level() -> str:
    """Минимальный уровень выводимых записей.

    Returns:
        str: Имя уровня логирования.
    """
    return os.getenv("APP_LOG_LEVEL", "INFO")


def app_cors_allowed_origins() -> list[str]:
    """Список источников, которым разрешено вызывать API.

    Пустой список полностью выключает междоменное выполнение.

    Returns:
        list[str]: Разрешённые источники.
    """
    return as_list(os.getenv("APP_CORS_ALLOWED_ORIGINS", ""))


def frontend_dist() -> str:
    """Каталог с собранным интерфейсом, который раздаёт бэкенд.

    Пустое значение означает, что путь достраивается из раскладки репозитория и
    образа: рабочая копия и контейнер держат сборку в разных местах.

    Returns:
        str: Настроенный путь или пустая строка, когда путь не задан.
    """
    return os.getenv("FRONTEND_DIST", "")
