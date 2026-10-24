"""Сборка контейнера зависимостей одного процесса.

Композиционный корень делает ровно две вещи: решает, с какой конфигурацией
процесс живёт, и решает, какие соавторы презентационного слоя в игре. Всё
остальное объявляют провайдеры этого пакета.

Одно из значений контекста — формулировки сообщений. Их пишет презентационный
слой, поэтому сюда они приходят извне, а без них контейнер собирает пустые
уведомления вместо выдуманных здесь.
"""

from __future__ import annotations

from dishka import AsyncContainer, make_async_container

from backend.application.interface.services.notification_factory import NotificationFactory
from backend.config.settings import Settings
from backend.infrastructure.di.providers import (
    AccountProvider,
    AutomationProvider,
    BoardProvider,
    CommandProvider,
    CoreProvider,
    DeviceProvider,
    DomainProvider,
    EspProvider,
    HomeProvider,
    LanguageProvider,
    PersistenceProvider,
    PersonalizationProvider,
    ScenarioProvider,
    SecurityProvider,
    TelegramProvider,
    VolatileStateProvider,
)
from backend.infrastructure.di.silent_notifications import SilentNotificationFactory

Container = AsyncContainer

PROVIDERS = (
    CoreProvider(),
    SecurityProvider(),
    PersistenceProvider(),
    VolatileStateProvider(),
    LanguageProvider(),
    TelegramProvider(),
    DomainProvider(),
    EspProvider(),
    HomeProvider(),
    AutomationProvider(),
    ScenarioProvider(),
    CommandProvider(),
    AccountProvider(),
    DeviceProvider(),
    BoardProvider(),
    PersonalizationProvider(),
)


def build_dishka_container(
    settings: Settings,
    *,
    notifications: NotificationFactory | None = None,
) -> Container:
    """Собирает граф зависимостей одного процесса.

    Args:
        settings: Конфигурация, из которой строится граф.
        notifications: Строит формулировки каждого сообщения человека.

    Returns:
        Container: Контейнер со всем, что нужно процессу.
    """
    context = {
        Settings: settings,
        NotificationFactory: notifications or SilentNotificationFactory(),
    }
    return make_async_container(*PROVIDERS, context=context)
