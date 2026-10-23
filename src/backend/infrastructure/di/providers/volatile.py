"""Недолгое состояние: хранилище дома, поток событий, чаты мессенджера и аренда."""

from __future__ import annotations

from dishka import Provider, Scope, provide
from redis.asyncio import Redis

from backend.application.interface.services.distributed_lock import DistributedLock
from backend.application.interface.services.home_state_store import HomeStateStore
from backend.application.interface.services.realtime_publisher import RealtimePublisher
from backend.config.settings import Settings
from backend.infrastructure.redis.chat_sessions import RedisChatSessionStore
from backend.infrastructure.redis.event_broker import RedisEventBroker, RedisSubscriber
from backend.infrastructure.redis.locks import RedisDistributedLock
from backend.infrastructure.redis.state_store import RedisHomeStateStore

APP = Scope.APP


class VolatileStateProvider(Provider):
    """Хранилище живого состояния, поток событий, чаты и аренда."""

    @provide(scope=APP)
    def state_store(self, redis: Redis, settings: Settings) -> HomeStateStore:
        """Собирает надёжное жилище всего недолгого."""
        return RedisHomeStateStore(redis, settings.redis_key_prefix)

    @provide(scope=APP)
    def realtime(self, redis: Redis, settings: Settings) -> RealtimePublisher:
        """Собирает издателя событий в реальном времени."""
        return RedisEventBroker(redis, settings.redis_key_prefix)

    @provide(scope=APP)
    def subscriber(self, settings: Settings) -> RedisSubscriber:
        """Собирает подписку, из которой читает концентратор."""
        return RedisSubscriber(
            url=settings.redis_url,
            password=settings.redis_password,
            key_prefix=settings.redis_key_prefix,
        )

    @provide(scope=APP)
    def chat_sessions(self, redis: Redis, settings: Settings) -> RedisChatSessionStore:
        """Собирает соответствие чатов аккаунтам."""
        return RedisChatSessionStore(redis, settings.redis_key_prefix)

    @provide(scope=APP)
    def lock(self, redis: Redis, settings: Settings) -> DistributedLock:
        """Собирает аренду, не пускающую два воркера к одному аккаунту."""
        return RedisDistributedLock(redis, key_prefix=settings.redis_key_prefix)
