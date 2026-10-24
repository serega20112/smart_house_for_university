"""Сборка графа фонового процесса: конфигурация, роль и формулировки сообщений.

Рабочий не поднимает портов и не строит приложение — ему нужен только граф, в
котором шлюз железа смотрит в шину команд. Формулировки уведомлений приходят
отсюда, потому что они принадлежат презентационному слою: знать о нём вправе только
композиция, а без них сценарий завершался бы молчанием.
"""

from __future__ import annotations

from backend.config.settings import Settings
from backend.infrastructure.di import Container, ProcessRole, build_dishka_container
from backend.presentation.messages import NotificationFactoryImpl


def build_worker_container(settings: Settings) -> Container:
    """Собирает граф зависимостей фонового процесса.

    Args:
        settings: Конфигурация развёртывания.

    Returns:
        Container: Контейнер роли рабочего — со шлюзом поверх шины команд и без
        сервера плат.
    """
    return build_dishka_container(
        settings,
        notifications=NotificationFactoryImpl(),
        role=ProcessRole.WORKER,
    )
