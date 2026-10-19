"""Volatile and shared state of the smart home backend.

Everything that has to outlive a process without belonging in the relational
store lives here: the state of every home, the realtime event stream and the
Telegram chats linked to accounts. The module only owns adapters; deciding what
the state means belongs to the application layer.
"""

from backend.infrastructure.redis.chat_sessions import RedisChatSessionStore
from backend.infrastructure.redis.event_broker import (
    PublishedEvent,
    RedisEventBroker,
    RedisSubscriber,
)
from backend.infrastructure.redis.state_store import RedisHomeStateStore

__all__ = [
    "PublishedEvent",
    "RedisChatSessionStore",
    "RedisEventBroker",
    "RedisHomeStateStore",
    "RedisSubscriber",
]
