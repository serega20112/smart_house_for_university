"""Одноразовые билеты интерфейса в Redis: REST выдаёт, WebSocket гасит.

Билет живёт несколько секунд и принадлежит только тому процессу чтения, что его
выпускает, поэтому хранение в Redis — тот же приём, что и для присутствия плат: любой
процесс API может выдать билет, а любой процесс, держащий соединение, его погасит.
Погашение делает `GETDEL`: атомарный читает-и-удаляет, из-за которого два одновременных
обмена одним билетом не пройдут оба — второй увидит пустоту.
"""

from __future__ import annotations

import secrets

from redis.asyncio import Redis as AsyncRedis

from backend.application.interfaces.services.security.realtime_ticket_store import (
    RealtimeTicketStore,
)
from backend.domain.identifiers import UserId
from backend.infrastructure.brokers import keys

TICKET_BYTES = 24


class RedisRealtimeTicketStore(RealtimeTicketStore):
    """Хранилище одноразовых билетов поверх Redis с коротким сроком жизни.

    Args:
        redis: Асинхронное соединение, в котором живут билеты.
        key_prefix: Пространство имён, с которого начинается каждый ключ.
        ttl_sec: Сколько секунд билет остаётся годным до обмена или истечения.
    """

    def __init__(self, redis: AsyncRedis, key_prefix: str, ttl_sec: float) -> None:
        """Инициализирует хранилище билетов.

        Args:
            redis: Асинхронное соединение, в котором живут билеты.
            key_prefix: Пространство имён, с которого начинается каждый ключ.
            ttl_sec: Сколько секунд билет остаётся годным.
        """
        self._redis = redis
        self._prefix = key_prefix
        self._ttl_sec = ttl_sec

    async def issue(self, user_id: UserId) -> str:
        """Открывает билет на аккаунт и запоминает его владельца на срок жизни.

        Args:
            user_id: Аккаунт, чьё соединение будет открыто по этому билету.

        Returns:
            str: Непредсказуемая строка билета, годная ровно на один обмен.
        """
        ticket = secrets.token_urlsafe(TICKET_BYTES)
        await self._redis.set(
            keys.realtime_ticket_key(self._prefix, ticket),
            str(user_id),
            ex=self._ttl(),
        )
        return ticket

    async def redeem(self, ticket: str) -> UserId | None:
        """Обменивает билет на аккаунт ровно один раз.

        Args:
            ticket: Строка билета из строки запроса соединения.

        Returns:
            UserId | None: Аккаунт билета или None, когда билет пуст, истёк или
                уже был погашен.
        """
        if not ticket:
            return None
        owner = await self._redis.getdel(keys.realtime_ticket_key(self._prefix, ticket))
        if owner is None:
            return None
        return UserId.parse(owner.decode() if isinstance(owner, bytes) else owner)

    def _ttl(self) -> int:
        """Возвращает срок жизни билета целым числом секунд, каким его требует Redis."""
        return max(1, round(self._ttl_sec))
