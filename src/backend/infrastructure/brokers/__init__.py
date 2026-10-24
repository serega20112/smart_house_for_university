"""Адаптеры брокера и кеша на Redis: недолгое и общее состояние бэкенда.

Здесь живёт всё, что должно пережить процесс, но не относится к реляционному
хранилищу: состояние каждого дома, поток событий в реальном времени, чаты
мессенджера, привязанные к аккаунтам, и аренда, по которой два воркера не
берут один дом. Модули пакета держат только адаптеры; решать, что состояние
значит, продолжает прикладной слой.

Имена ключей и каналов собирает :mod:`keys`, разбор сырых ответов —
:mod:`decoding`, а то, как состояние дома лежит в хешах и Lua-скриптах, —
:mod:`state_schema`.
"""

from backend.infrastructure.brokers.chat_sessions import RedisChatSessionStore
from backend.infrastructure.brokers.event_broker import (
    PublishedEvent,
    RedisEventBroker,
    RedisSubscriber,
)
from backend.infrastructure.brokers.locks import RedisDistributedLock
from backend.infrastructure.brokers.state_store import RedisHomeStateStore

__all__ = [
    "PublishedEvent",
    "RedisChatSessionStore",
    "RedisDistributedLock",
    "RedisEventBroker",
    "RedisHomeStateStore",
    "RedisSubscriber",
]
