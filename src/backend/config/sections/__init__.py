"""Загрузчики значений конфигурации по секциям.

Каждый модуль читает переменные окружения в момент вызова, поэтому перезагрузка
модуля пересобирает настройки из текущего окружения.
"""

from backend.config.sections import (
    auth,
    automation,
    board,
    database,
    devices,
    http,
    language,
    redis_,
    security,
    server,
    telegram,
    worker,
)

__all__ = [
    "auth",
    "automation",
    "board",
    "database",
    "devices",
    "http",
    "language",
    "redis_",
    "security",
    "server",
    "telegram",
    "worker",
]
