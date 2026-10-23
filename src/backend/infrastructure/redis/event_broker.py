"""Realtime events over Redis Pub/Sub.

An event reaches one account through its own channel and a fact that belongs to
nobody in particular through the global channel. Subscribers read both streams
from a blocking client, which is why :class:`RedisSubscriber` owns its own
synchronous connection instead of borrowing the asynchronous one: ``pubsub.listen``
blocks, and blocking the event loop of a request would be worse than a second
connection.

Nothing here knows about sockets. The websocket hub of the presentation layer
consumes the async iterable and forwards the events wherever it likes.
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
    """One event that reached a channel.

    Args:
        user_id: Owner the event was addressed to, or None for a global event.
        event: Stable machine readable event name.
        payload: JSON serializable event data.

    Returns:
        None.
    """

    user_id: UserId | None
    event: str
    payload: dict[str, Any]


class RedisEventBroker(RealtimePublisher):
    """Publishes events into one channel per account plus a global channel.

    Args:
        redis: Asynchronous connection the events are written to.
        key_prefix: Namespace every channel of this adapter starts with.

    Returns:
        None.
    """

    def __init__(self, redis: AsyncRedis, key_prefix: str) -> None:
        """Initialize the broker.

        Args:
            redis: Asynchronous connection the events are written to.
            key_prefix: Namespace every channel of this adapter starts with.

        Returns:
            None.
        """
        self._redis = redis
        self._prefix = key_prefix

    async def publish(self, user_id: UserId, event: str, payload: dict[str, Any]) -> None:
        """Send an event to the clients of one account.

        Args:
            user_id: Owner the event belongs to.
            event: Stable machine readable event name.
            payload: JSON serializable event data.

        Returns:
            None.
        """
        await self._redis.publish(self._user_channel(user_id), _encode(user_id, event, payload))

    async def broadcast(self, event: str, payload: dict[str, Any]) -> None:
        """Send an event to every connected client.

        Args:
            event: Stable machine readable event name.
            payload: JSON serializable event data.

        Returns:
            None.
        """
        await self._redis.publish(self._global_channel(), _encode(None, event, payload))

    def _user_channel(self, user_id: UserId) -> str:
        """Возвращает канал одного аккаунта."""
        return keys.user_channel(self._prefix, user_id)

    def _global_channel(self) -> str:
        """Возвращает канал, обращённый ко всем."""
        return keys.global_channel(self._prefix)


class RedisSubscriber:
    """Blocking subscriber presented as an async iterable.

    The blocking ``pubsub.listen`` loop runs on its own thread and hands every
    message to the event loop through an unbounded queue, so a consumer may
    simply ``async for`` over the stream from inside a request handler.

    Args:
        url: Connection URL of a synchronous Redis client.
        password: Password of the connection, or None when it is open.
        key_prefix: Namespace every channel of this adapter starts with.

    Returns:
        None.
    """

    def __init__(self, url: str, password: str | None, key_prefix: str) -> None:
        """Initialize the subscriber.

        Args:
            url: Connection URL of a synchronous Redis client.
            password: Password of the connection, or None when it is open.
            key_prefix: Namespace every channel of this adapter starts with.

        Returns:
            None.
        """
        self._url = url
        self._password = password
        self._prefix = key_prefix

    async def stream(self, user_id: UserId | None = None) -> AsyncIterator[PublishedEvent]:
        """Yield every event addressed to an account and to everybody.

        Args:
            user_id: Owner whose channel is subscribed to, or None to subscribe
                to the global channel only.

        Yields:
            PublishedEvent: Events as they arrive, in arrival order.
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
