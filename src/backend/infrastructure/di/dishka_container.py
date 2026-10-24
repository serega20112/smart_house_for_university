"""Сборка контейнера зависимостей одного процесса.

Композиционный корень делает ровно две вещи: решает, с какой конфигурацией
процесс живёт, и решает, какие соавторы презентационного слоя в игре. Всё
остальное объявляют провайдеры этого пакета.

Одно из значений контекста — формулировки сообщений. Их пишет презентационный
слой, поэтому сюда они приходят извне, а без них контейнер собирает пустые
уведомления вместо выдуманных здесь.
"""

from __future__ import annotations

from enum import Enum, auto

from dishka import AsyncContainer, Provider, make_async_container

from backend.application.interfaces.services.messaging.notification_factory import (
    NotificationFactory,
)
from backend.config.settings import Settings
from backend.infrastructure.di.providers import (
    AccountsUseCaseProvider,
    AutomationUseCaseProvider,
    BoardCoordinationProvider,
    BoardRemoteProvider,
    BoardSocketProvider,
    BoardsUseCaseProvider,
    BrokersProvider,
    CommandsUseCaseProvider,
    DatabaseProvider,
    DevicesUseCaseProvider,
    HomeUseCaseProvider,
    PersistenceProvider,
    PersonalizationUseCaseProvider,
    PhrasesProvider,
    RuntimeProvider,
    ScenariosUseCaseProvider,
    SecurityProvider,
    TelegramProvider,
    WebSocketsProvider,
)
from backend.infrastructure.di.silent_notifications import SilentNotificationFactory

Container = AsyncContainer


class ProcessRole(Enum):
    """Роль процесса, для которого собирается контейнер.

    Attributes:
        API: Процесс интерфейса — единственный владелец WebSocket-сервера плат.
        WORKER: Фоновый процесс — автоматика и сценарии, говорящий с железа через шину.
    """

    API = auto()
    WORKER = auto()


SHARED_PROVIDERS: tuple[Provider, ...] = (
    RuntimeProvider(),
    DatabaseProvider(),
    PersistenceProvider(),
    BrokersProvider(),
    SecurityProvider(),
    PhrasesProvider(),
    TelegramProvider(),
    WebSocketsProvider(),
    BoardCoordinationProvider(),
    HomeUseCaseProvider(),
    AutomationUseCaseProvider(),
    ScenariosUseCaseProvider(),
    CommandsUseCaseProvider(),
    AccountsUseCaseProvider(),
    DevicesUseCaseProvider(),
    BoardsUseCaseProvider(),
    PersonalizationUseCaseProvider(),
)

ROLE_PROVIDERS: dict[ProcessRole, tuple[Provider, ...]] = {
    ProcessRole.API: (
        BoardSocketProvider(),
    ),
    ProcessRole.WORKER: (
        BoardRemoteProvider(),
    ),
}


def build_dishka_container(
    settings: Settings,
    *,
    notifications: NotificationFactory | None = None,
    role: ProcessRole = ProcessRole.API,
) -> Container:
    """Собирает граф зависимостей одного процесса.

    Разделение провайдеров по ролям — суть исправления P0-2: сервер плат заводится
    только в процессе API, а рабочий получает удалённый шлюз и не может поднять
    второй WebSocket-сервер на занятом порту.

    Args:
        settings: Конфигурация, из которой строится граф.
        notifications: Строит формулировки каждого сообщения человека.
        role: Роль процесса, определяющая набор ролевых провайдеров.

    Returns:
        Container: Контейнер со всем, что нужно процессу.
    """
    context = {
        Settings: settings,
        NotificationFactory: notifications or SilentNotificationFactory(),
    }
    providers = (*SHARED_PROVIDERS, *ROLE_PROVIDERS[role])
    return make_async_container(*providers, context=context)
