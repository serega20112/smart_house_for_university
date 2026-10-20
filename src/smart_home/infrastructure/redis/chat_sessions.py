"""Which Telegram chat belongs to which account.

The mapping is kept in Redis rather than in the process so a restart of the
backend does not log everybody out of the bot. Nothing secret is written here:
the entry holds the chat identifier and the account identifier, which the bot
already knows, and no password ever reaches this store or the messenger.
"""

from __future__ import annotations

from redis.asyncio import Redis

from smart_home.domain.identifiers import UserId

CHAT_KEY = "chat"
USER_KEY = "user"


class RedisChatSessionStore:
    """Maps Telegram chats onto accounts in both directions.

    Args:
        redis: Connection the mapping is stored in.
        key_prefix: Namespace every key of this adapter starts with.

    Returns:
        None.
    """

    def __init__(self, redis: Redis, key_prefix: str) -> None:
        """Initialize the store.

        Args:
            redis: Connection the mapping is stored in.
            key_prefix: Namespace every key of this adapter starts with.

        Returns:
            None.
        """
        self._redis = redis
        self._prefix = key_prefix

    async def bind(self, chat_id: int, user_id: UserId) -> None:
        """Remember which account a chat belongs to.

        Args:
            chat_id: Telegram chat the account was linked from.
            user_id: Owner linked to that chat.

        Returns:
            None.
        """
        async with self._redis.pipeline(transaction=True) as pipe:
            pipe.set(f"{self._prefix}:{CHAT_KEY}:{chat_id}", str(user_id))
            pipe.set(f"{self._prefix}:{USER_KEY}:{user_id}", str(chat_id))
            await pipe.execute()

    async def user_of(self, chat_id: int) -> UserId | None:
        """Return the account a chat was linked to.

        Args:
            chat_id: Telegram chat the message arrived in.

        Returns:
            UserId | None: Linked account, or None when the chat was never
            linked.
        """
        raw = await self._redis.get(f"{self._prefix}:{CHAT_KEY}:{chat_id}")
        return None if raw is None else UserId.parse(_text(raw))

    async def chat_of(self, user_id: UserId) -> int | None:
        """Return the chat a user should be notified in.

        Args:
            user_id: Owner a notification is about.

        Returns:
            int | None: Linked chat, or None when the user never linked one.
        """
        raw = await self._redis.get(f"{self._prefix}:{USER_KEY}:{user_id}")
        return None if raw is None else int(_text(raw))

    async def forget(self, chat_id: int) -> None:
        """Remove the account a chat was linked to.

        Args:
            chat_id: Telegram chat the account was linked from.

        Returns:
            None.
        """
        user_id = await self.user_of(chat_id)
        if user_id is None:
            return
        await self._redis.delete(
            f"{self._prefix}:{CHAT_KEY}:{chat_id}", f"{self._prefix}:{USER_KEY}:{user_id}"
        )


def _text(raw: bytes | str) -> str:
    return raw.decode("utf-8") if isinstance(raw, bytes) else raw
