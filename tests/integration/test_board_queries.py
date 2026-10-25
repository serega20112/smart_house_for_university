"""Чтения плат на живой PostgreSQL: список открытых предложений знает про срок.

Объявление платы живёт две минуты, и с последней секунды его уже нельзя забрать.
Значит, и показывать его незачем: чтение обязано отсечь истёкшее, а не ждать, пока
его сотрёт фоновая чистка. Проверка идёт к настоящей базе, потому что фильтр живёт
в запросе.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from sqlalchemy.ext.asyncio import async_sessionmaker

from backend.domain.entities.esp_claim.esp_claim import EspClaim
from backend.domain.value_objects.boards.pairing_key import PairingKey
from backend.infrastructure.database.queries.boards import SqlBoardQueries
from backend.infrastructure.database.repositories.claim_repository import SqlClaimRepository

NOW = datetime(2027, 5, 1, 12, 0, tzinfo=UTC)


async def test_expired_claim_is_not_listed(
    sql_session_factory: async_sessionmaker,
) -> None:
    """Действительное объявление видно, истёкшее — уже нет."""
    live = EspClaim.announce(
        device_key=PairingKey.generate(), label="LIVE", announced_at=NOW, ttl_sec=120
    )
    stale = EspClaim.announce(
        device_key=PairingKey.generate(),
        label="STALE",
        announced_at=NOW - timedelta(minutes=5),
        ttl_sec=60,
    )
    async with sql_session_factory() as session:
        repository = SqlClaimRepository(session)
        await repository.add(live)
        await repository.add(stale)
        await session.flush()

    queries = SqlBoardQueries(sql_session_factory)

    # Полминуты спустя: у LIVE срок ещё не вышел, у STALE вышел четыре минуты назад.
    labels = [claim.label for claim in await queries.list_open_claims(NOW + timedelta(seconds=30))]
    assert labels == ["LIVE"]

    # За пять минут до этого ещё не истёк срок и у STALE: фильтр смотрит на срок,
    # а не на возраст объявления.
    both = [claim.label for claim in await queries.list_open_claims(NOW - timedelta(seconds=300))]
    assert sorted(both) == ["LIVE", "STALE"]
