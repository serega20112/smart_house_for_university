"""Брокер недолгого состояния: соединение Redis и всё, что на нём держится."""

from __future__ import annotations

from collections.abc import AsyncIterator

from dishka import Provider, Scope, provide
from redis.asyncio import Redis

from backend.application.interfaces.services.messaging.realtime_publisher import RealtimePublisher
from backend.application.interfaces.services.state.home_state_store import HomeStateStore
from backend.application.interfaces.services.system.distributed_lock import DistributedLock
from backend.config.settings import Settings
from backend.infrastructure.brokers.chat_sessions import RedisChatSessionStore
from backend.infrastructure.brokers.event_broker import RedisEventBroker, RedisSubscriber
from backend.infrastructure.brokers.locks import RedisDistributedLock
from backend.infrastructure.brokers.state_store import RedisHomeStateStore

APP = Scope.APP


class BrokersProvider(Provider):
    """Соединение с Redis, хранилище домов, поток событий, чаты и аренда."""

    @provide(scope=APP)
    async def redis(self, settings: Settings) -> AsyncIterator[Redis]:
        """Собирает соединение, в котором лежит всё недолгое."""
        client: Redis = Redis.from_url(
            settings.redis_url,
            password=settings.redis_password,
        )
        yield client
        await client.aclose()

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
