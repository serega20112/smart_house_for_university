"""Подписка читает Redis-события асинхронно и не оставляет следов после закрытия.

Это проверка P0-4: подписка на события построена на ``redis.asyncio`` без единого
потока и блокирующего listen, поэтому каждое обращение открывает собственную подписку и
обязана вернуть соединение, когда потребитель уходит. Первый тест показывает, что
опубликованное событие доходит до подписчика; второй — что многократное открытие и
закрытие подписки не наращивает число потоков, то есть не оставляет висящих читателей.
"""

from __future__ import annotations

import asyncio
import threading
from contextlib import suppress

from fakeredis import FakeServer, aioredis

from backend.domain.identifiers import UserId
from backend.infrastructure.brokers import keys
from backend.infrastructure.brokers.event_broker import RedisEventBroker, RedisSubscriber
from tests.conftest import OWNER_UUID

PREFIX = "tests"


def make_redis() -> aioredis.FakeRedis:
    """Строит асинхронное фейковое соединение с декодированием ответов.

    Returns:
        aioredis.FakeRedis: Клиент поверх чистого сервера.
    """
    return aioredis.FakeRedis(server=FakeServer(), decode_responses=True)


async def test_stream_delivers_published_event():
    """Опубликованное событие приходит подписчику этого аккаунта.

    Returns:
        None: Только проверка сквозной доставки.
    """
    redis = make_redis()
    user = UserId.parse(OWNER_UUID)
    broker = RedisEventBroker(redis, PREFIX)
    subscriber = RedisSubscriber(redis, PREFIX)

    stream = subscriber.stream(user)
    reader = asyncio.create_task(stream.__anext__())
    await asyncio.sleep(0.1)
    await broker.publish(user, "device.state_changed", {"channel": 3})

    event = await asyncio.wait_for(reader, timeout=2.0)
    await stream.aclose()

    assert event.event == "device.state_changed"
    assert event.payload == {"channel": 3}
    assert event.user_id == user


async def test_broken_frame_does_not_kill_the_subscription():
    """Испорченный кадр пропускается, а подписка продолжает отдавать события.

    Returns:
        None: Только проверка того, что битый кадр не закрывает поток.
    """
    redis = make_redis()
    user = UserId.parse(OWNER_UUID)
    broker = RedisEventBroker(redis, PREFIX)
    subscriber = RedisSubscriber(redis, PREFIX)

    stream = subscriber.stream(user)
    reader = asyncio.create_task(stream.__anext__())
    await asyncio.sleep(0.1)
    channel = keys.user_channel(PREFIX, user)
    await redis.publish(channel, "not a frame at all")
    await redis.publish(channel, '{"user_id":"not-a-uuid","event":"stale","payload":{}}')
    await broker.publish(user, "device.state_changed", {"channel": 4})

    event = await asyncio.wait_for(reader, timeout=2.0)
    await stream.aclose()

    assert event.event == "device.state_changed"
    assert event.payload == {"channel": 4}


async def test_repeated_subscription_leaves_no_threads_behind():
    """Каждая подписка закрывается и не наращивает живущие потоки.

    Returns:
        None: Только проверка отсутствия утечки потоков.
    """
    redis = make_redis()
    user = UserId.parse(OWNER_UUID)
    subscriber = RedisSubscriber(redis, PREFIX)

    before = threading.active_count()
    for _ in range(5):
        stream = subscriber.stream(user)
        reader = asyncio.create_task(stream.__anext__())
        await asyncio.sleep(0.05)
        reader.cancel()
        with suppress(asyncio.CancelledError):
            await reader
        await stream.aclose()

    assert threading.active_count() == before
