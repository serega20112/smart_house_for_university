"""События протокола через Redis Pub/Sub.

Событие доходит до одного аккаунта через его собственный канал, а факт, который ни к
кому конкретно не обращён, — через общий канал. Подписчики читают оба потока блокирующим
клиентом, поэтому :class:`RedisSubscriber` владеет собственным синхронным соединением, а
не одалживает асинхронное: ``pubsub.listen`` блокирует, и блокировать цикл событий
запросом было бы хуже второго соединения.

Здесь никто не знает про сокеты. Асинхронный итерируемый поток потребляет концентратор
вебсокетов презентационного слоя и раздаёт события куда ему угодно.
"""

from __future__ import annotations

import asyncio
import json
import threading
from collections.abc import AsyncIterator
from dataclasses import dataclass
from datetime import UTC, datetime
from queue import Queue
from typing import Any

import redis
from redis.asyncio import Redis as AsyncRedis

from backend.application.interface.services.realtime_publisher import RealtimePublisher
from backend.domain.identifiers import UserId
from backend.infrastructure.logging import get_logger
from backend.infrastructure.redis import keys

log = get_logger("redis.event_broker")

CLOSING = object()


@dataclass(frozen=True, slots=True)
class PublishedEvent:
    """Одно событие, дошедшее до канала.

    Attributes:
        user_id: Владелец, которому событие адресовали, или None для общего.
        event: Постоянное машинночитаемое имя события.
        payload: Данные события, сериализуемые в JSON.
    """

    user_id: UserId | None
    event: str
    payload: dict[str, Any]


class RedisEventBroker(RealtimePublisher):
    """Публикует события в канал одного аккаунта плюс общий канал.

    Attributes:
        redis: Асинхронное соединение, куда пишут события.
        key_prefix: Пространство имён, с которого начинается каждый канал адаптера.
    """

    def __init__(self, redis: AsyncRedis, key_prefix: str) -> None:
        """Инициализирует издатель.

        Args:
            redis: Асинхронное соединение, куда пишут события.
            key_prefix: Пространство имён, с которого начинается каждый канал адаптера.
        """
        self._redis = redis
        self._prefix = key_prefix

    async def publish(self, user_id: UserId, event: str, payload: dict[str, Any]) -> None:
        """Отправляет событие клиентам одного аккаунта.

        Args:
            user_id: Владелец, к которому событие относится.
            event: Постоянное машинночитаемое имя события.
            payload: Данные события, сериализуемые в JSON.
        """
        await self._redis.publish(self._user_channel(user_id), _encode(user_id, event, payload))

    async def broadcast(self, event: str, payload: dict[str, Any]) -> None:
        """Отправляет событие каждому подключённому клиенту.

        Args:
            event: Постоянное машинночитаемое имя события.
            payload: Данные события, сериализуемые в JSON.
        """
        await self._redis.publish(self._global_channel(), _encode(None, event, payload))

    def _user_channel(self, user_id: UserId) -> str:
        """Возвращает канал одного аккаунта."""
        return keys.user_channel(self._prefix, user_id)

    def _global_channel(self) -> str:
        """Возвращает канал, обращённый ко всем."""
        return keys.global_channel(self._prefix)


class RedisSubscriber:
    """Блокирующий подписчик, представленный как асинхронный итерируемый поток.

    Цикл блокирующего ``pubsub.listen`` крутится на собственном потоке и передаёт
    каждое сообщение в цикл событий через неограниченную очередь, поэтому потребитель
    может просто писать ``async for`` по потоку из обработчика запроса.

    Attributes:
        url: Адрес подключения синхронного клиента Redis.
        password: Пароль подключения или None, когда соединение открытое.
        key_prefix: Пространство имён, с которого начинается каждый канал адаптера.
    """

    def __init__(self, url: str, password: str | None, key_prefix: str) -> None:
        """Инициализирует подписчика.

        Args:
            url: Адрес подключения синхронного клиента Redis.
            password: Пароль подключения или None, когда соединение открытое.
            key_prefix: Пространство имён, с которого начинается каждый канал адаптера.
        """
        self._url = url
        self._password = password
        self._prefix = key_prefix

    async def stream(self, user_id: UserId | None = None) -> AsyncIterator[PublishedEvent]:
        """Отдаёт всякое событие, адресованное аккаунту и всем сразу.

        Args:
            user_id: Владелец, на чей канал подписываются, или None, чтобы подписаться
                только на общий канал.

        Yields:
            PublishedEvent: События по мере прихода, в порядке прихода.
        """
        channels = self._channels(user_id)
        client = redis.Redis.from_url(self._url, password=self._password)
        pubsub = client.pubsub(ignore_subscribe_messages=True)
        incoming: Queue[PublishedEvent | object] = Queue()

        def pump() -> None:
            try:
                for message in pubsub.listen():
                    received = _decode(message)
                    if received is not None:
                        incoming.put(received)
            except Exception as error:
                log.error("redis.subscription_failed", error=str(error))
            finally:
                incoming.put(CLOSING)

        thread = threading.Thread(target=pump, name="redis-subscriber", daemon=True)
        pubsub.subscribe(*channels)
        thread.start()
        try:
            while True:
                message = await _next(incoming)
                if message is CLOSING:
                    return
                if isinstance(message, PublishedEvent):
                    yield message
        finally:
            pubsub.close()

    def _channels(self, user_id: UserId | None) -> tuple[str, ...]:
        """Возвращает каналы, на которые нужно подписаться."""
        subscribed = keys.global_channel(self._prefix)
        if user_id is None:
            return (subscribed,)
        return (keys.user_channel(self._prefix, user_id), subscribed)


async def _next(incoming: Queue[PublishedEvent | object]) -> PublishedEvent | object:
    return await asyncio.to_thread(incoming.get)


def _encode(user_id: UserId | None, event: str, payload: dict[str, Any]) -> str:
    return json.dumps(
        {
            "user_id": None if user_id is None else str(user_id),
            "event": event,
            "payload": payload,
            "published_at": datetime.now(UTC).isoformat(),
        },
        ensure_ascii=False,
        separators=(",", ":"),
    )


def _decode(message: dict[str, Any]) -> PublishedEvent | None:
    raw = message.get("data")
    if not isinstance(raw, (str, bytes, bytearray)):
        return None
    try:
        decoded = json.loads(raw)
    except ValueError:
        log.warning("redis.event_not_json", payload=str(raw)[:120])
        return None
    if not isinstance(decoded, dict):
        return None
    owner = decoded.get("user_id")
    payload = decoded.get("payload")
    return PublishedEvent(
        user_id=None if owner is None else UserId.parse(owner),
        event=str(decoded.get("event", "")),
        payload=payload if isinstance(payload, dict) else {},
    )
