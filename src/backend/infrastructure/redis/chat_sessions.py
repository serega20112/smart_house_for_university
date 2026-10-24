"""Какому аккаунту какой телеграм-чат принадлежит.

Соответствие держат в Redis, а не в процессе, поэтому перезапуск бэкенда не выбрасывает
всех из бота. Секрета здесь нет ничего: запись хранит идентификатор чата и идентификатор
аккаунта, которые боту и так известны, а пароль не попадает ни в это хранилище, ни в
мессенджер.
"""

from __future__ import annotations

from redis.asyncio import Redis

from backend.domain.identifiers import UserId
from backend.infrastructure.redis import keys
from backend.infrastructure.redis.decoding import as_text


class RedisChatSessionStore:
    """Ставит телеграм-чаты в соответствие аккаунтам в обе стороны.

    Attributes:
        redis: Соединение, в котором хранят соответствие.
        key_prefix: Пространство имён, с которого начинается каждый ключ адаптера.
    """

    def __init__(self, redis: Redis, key_prefix: str) -> None:
        """Инициализирует хранилище.

        Args:
            redis: Соединение, в котором хранят соответствие.
            key_prefix: Пространство имён, с которого начинается каждый ключ адаптера.
        """
        self._redis = redis
        self._prefix = key_prefix

    async def bind(self, chat_id: int, user_id: UserId) -> None:
        """Запоминает, какому аккаунту принадлежит чат.

        Args:
            chat_id: Телеграм-чат, из которого привязали аккаунт.
            user_id: Владелец, привязанный к этому чату.
        """
        async with self._redis.pipeline(transaction=True) as pipe:
            pipe.set(keys.chat_key(self._prefix, chat_id), str(user_id))
            pipe.set(keys.user_key(self._prefix, user_id), str(chat_id))
            await pipe.execute()

    async def user_of(self, chat_id: int) -> UserId | None:
        """Возвращает аккаунт, к которому привязан чат.

        Args:
            chat_id: Телеграм-чат, в котором пришло сообщение.

        Returns:
            UserId | None: Привязанный аккаунт или None, когда чат не привязывали.
        """
        raw = as_text(await self._redis.get(keys.chat_key(self._prefix, chat_id)))
        return None if raw is None else UserId.parse(raw)

    async def chat_of(self, user_id: UserId) -> int | None:
        """Возвращает чат, в котором надо уведомлять человека.

        Args:
            user_id: Владелец, о котором уведомление.

        Returns:
            int | None: Привязанный чат или None, когда человек ничего не привязал.
        """
        raw = as_text(await self._redis.get(keys.user_key(self._prefix, user_id)))
        return None if raw is None else int(raw)

    async def forget(self, chat_id: int) -> None:
        """Забывает аккаунт, к которому был привязан чат.

        Args:
            chat_id: Телеграм-чат, из которого привязали аккаунт.
        """
        user_id = await self.user_of(chat_id)
        if user_id is None:
            return
        await self._redis.delete(
            keys.chat_key(self._prefix, chat_id), keys.user_key(self._prefix, user_id)
        )
