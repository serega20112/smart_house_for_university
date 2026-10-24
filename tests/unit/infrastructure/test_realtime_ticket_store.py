"""Одноразовый билет обменивается на аккаунт ровно один раз.

Эти проверки держат суть 5.5.1: WebSocket открывается не по вечному токену сессии, а по
короткому билету, который гасится при первом обмене. Поэтому здесь видны обмен удавшегося
билета, отказ уже погашенному, отказ неизвестному и пустому, а также то, что значение
читается и при соединении без автоматической декодировки строк.
"""

from __future__ import annotations

from fakeredis import FakeServer, aioredis

from backend.domain.identifiers import UserId
from backend.infrastructure.brokers.realtime_tickets import RedisRealtimeTicketStore

PREFIX = "tests"


def make_store(*, ttl_sec: float = 30.0, decode: bool = True) -> RedisRealtimeTicketStore:
    """Строит хранилище билетов поверх чистого фейкового Redis.

    Args:
        ttl_sec: Срок жизни билета.
        decode: Включена ли автоматическая декодировка ответов соединения.

    Returns:
        RedisRealtimeTicketStore: Хранилище на свежем соединении.
    """
    redis = aioredis.FakeRedis(server=FakeServer(), decode_responses=decode)
    return RedisRealtimeTicketStore(redis, PREFIX, ttl_sec)


async def test_ticket_exchanges_for_its_account_once() -> None:
    """Выданный билет отдаёт аккаунт, а повторный обмен уже не удаётся.

    Returns:
        None: Только проверка одноразовости обмена.
    """
    store = make_store()
    user = UserId.generate()

    ticket = await store.issue(user)

    assert ticket
    assert await store.redeem(ticket) == user
    assert await store.redeem(ticket) is None


async def test_unknown_and_empty_tickets_are_refused() -> None:
    """Неизвестный и пустой билет не открывают доступ ни к кому.

    Returns:
        None: Только проверка отказа.
    """
    store = make_store()

    assert await store.redeem("never-issued") is None
    assert await store.redeem("") is None


async def test_ticket_survives_a_connection_without_string_decoding() -> None:
    """Соединение, отдающее байты, всё равно обменивает билет на аккаунт.

    Returns:
        None: Только проверка чтения значения без декодировки.
    """
    store = make_store(decode=False)
    user = UserId.generate()

    ticket = await store.issue(user)

    assert await store.redeem(ticket) == user
