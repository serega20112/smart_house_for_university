"""Внедрение зависимостей бэкенда умного дома.

Граф объявляют провайдеры этого пакета и собирает их :func:`build_dishka_container`,
которая возвращает Dishka ``AsyncContainer``. Процесс просит у контейнера то, что
ему нужно: транспорт плат и долгоживущие адаптеры прямо из области приложения, и
по одному свежнему набору сценариев из области запроса.
"""

from backend.infrastructure.di.dishka_container import Container, build_dishka_container

__all__ = [
    "Container",
    "build_dishka_container",
]
