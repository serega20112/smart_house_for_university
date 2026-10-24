"""События протокола через Redis Pub/Sub.

Событие доходит до одного аккаунта через его собственный канал, а факт, который ни к
кому конкретно не обращён, — через общий канал. Подписчик читает оба потока
асинхронным клиентом `redis.asyncio`: каждое сообщение приходит в цикл событий без
единого потока и без блокирующего `pubsub.listen`, поэтому одно соединение не утаскивает
за собой другое и не занимает общий пул потоков.

Здесь никто не знает про сокеты. Асинхронный итерируемый поток потребляет концентратор
вебсокетов презентационного слоя и раздаёт события куда ему угодно.
"""

from __future__ import annotations

import json
from collections.abc import AsyncIterator
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

from redis.asyncio import Redis as AsyncRedis

from backend.application.interfaces.services.messaging.realtime_publisher import RealtimePublisher
from backend.domain.identifiers import UserId
from backend.infrastructure.brokers import keys
from backend.infrastructure.system.logging import get_logger

log = get_logger("redis.event_broker")


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
    """Асинхронный подписчик, представленный итерируемым потоком событий.

    Каждое обращение к :meth:`stream` открывает собственную подписку поверх общего
    асинхронного соединения: ``redis.asyncio`` берёт для pub/sub отдельное соединение из
    пула и возвращает его обратно при закрытии, поэтому число одновременно живущих
    подписок ограничено размером пула и не разрастается фоновыми потоками.

    Attributes:
        redis: Асинхронное соединение, из которого берутся подписки.
        key_prefix: Пространство имён, с которого начинается каждый канал адаптера.
    """

    def __init__(self, redis: AsyncRedis, key_prefix: str) -> None:
        """Инициализирует подписчика.

        Args:
            redis: Асинхронное соединение, из которого берутся подписки.
            key_prefix: Пространство имён, с которого начинается каждый канал адаптера.
        """
        self._redis = redis
        self._prefix = key_prefix

    async def stream(self, user_id: UserId | None = None) -> AsyncIterator[PublishedEvent]:
        """Отдаёт всякое событие, адресованное аккаунту и всем сразу.

        Подписка закрывается и соединение возвращается в пул, когда потребитель
        выходит из потока или отменяет его: ни одна подписка не переживает того, кто
        её открыл.

        Args:
            user_id: Владелец, на чей канал подписываются, или None, чтобы подписаться
                только на общий канал.

        Yields:
            PublishedEvent: События по мере прихода, в порядке прихода.
        """
        channels = self._channels(user_id)
        pubsub = self._redis.pubsub(ignore_subscribe_messages=True)
        await pubsub.subscribe(*channels)
        try:
            while True:
                message = await pubsub.get_message(timeout=1.0)
                if message is None:
                    continue
                received = _decode(message)
                if received is not None:
                    yield received
        finally:
            await pubsub.unsubscribe(*channels)
            await pubsub.aclose()

    def _channels(self, user_id: UserId | None) -> tuple[str, ...]:
        """Возвращает каналы, на которые нужно подписаться."""
        subscribed = keys.global_channel(self._prefix)
        if user_id is None:
            return (subscribed,)
        return (keys.user_channel(self._prefix, user_id), subscribed)


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
