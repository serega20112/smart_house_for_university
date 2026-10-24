"""Сборка контейнера зависимостей одного процесса.

Провайдеры этого пакета объявляют граф, а эта функция выбирает из него то, что
принадлежит роли процесса. Общих провайдеров больше, чем ролевых, и это не
упущение: база, шина, безопасность и прикладные службы нужны обоим процессам
одинаково. Ролевыми остаются только те, что владеют ресурсом одного процесса:
сервер плат на порту 8001 и концентратор соединений интерфейса.

Формулировки сообщений пишет презентационный слой, поэтому сюда они приходят
внешним значением, а без них контейнер собирает пустые уведомления вместо
выдуманных здесь.
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
    ProcessRole.API: (BoardSocketProvider(), WebSocketsProvider()),
    ProcessRole.WORKER: (BoardRemoteProvider(),),
}


def build_dishka_container(
    settings: Settings,
    *,
    notifications: NotificationFactory | None = None,
    role: ProcessRole = ProcessRole.API,
) -> Container:
    """Собирает граф зависимостей одного процесса.

    Общие провайдеры идут в обоих процессах; ролевые добавляются к ним по роли.
    Роль API получает сервер плат и концентратор соединений — оба владеют
    ресурсом, который в системе бывает только один. Роль рабочего получает
    удалённый шлюз и поэтому не может поднять второй сервер на занятом порту.
    Уведомления остаются общими: оба процесса говорят с человеком, и рабочий
    сообщает о завершении сценария тем же каналом, что и интерфейс.

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
