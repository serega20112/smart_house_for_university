"""Two workers overlap without repeating the work of one account.

The lease is the only thing standing between two worker instances that pick up
the same period, so these tests exercise exactly that: the same job run twice
at the same moment over one shared server performs once, a second holder is
refused while the lease lives, and a lease taken away mid-work interrupts the
holder instead of letting it reach the board.
"""

from __future__ import annotations

import asyncio

import pytest
from fakeredis import aioredis

from backend.application.interfaces.services.system.distributed_lock import (
    LeaseLostError,
    LockBusyError,
)
from backend.domain.identifiers import UserId
from backend.infrastructure.brokers import keys
from backend.infrastructure.brokers.locks import RedisDistributedLock
from backend.infrastructure.workers.worker import WorkerLimits, run_for_each_user

PREFIX = "tests"
TTL_SEC = 30
REFRESH_SEC = 10
SHORT_TTL_SEC = 2
SHORT_REFRESH_SEC = 1
IO_TIMEOUT_SEC = 5.0

LIMITS = WorkerLimits(
    max_concurrent_users=2,
    per_user_timeout_sec=10,
    lock_ttl_sec=TTL_SEC,
    lock_refresh_sec=REFRESH_SEC,
)


def make_lock() -> RedisDistributedLock:
    """Build the lock over a fresh in-memory server.

    Returns:
        RedisDistributedLock: Lock backed by an isolated fake server.
    """
    return RedisDistributedLock(
        aioredis.FakeRedis(decode_responses=True),
        key_prefix=PREFIX,
        io_timeout_sec=IO_TIMEOUT_SEC,
    )


async def test_two_workers_run_each_account_exactly_once() -> None:
    """Two instances of the same period perform one run per account.

    Returns:
        None.
    """
    lock = make_lock()
    user_ids = [UserId.generate(), UserId.generate()]
    runs: list[str] = []

    async def run(user_id: UserId) -> None:
        """Record the run and hold the lease for a moment.

        Args:
            user_id: Account the cycle ran for.

        Returns:
            None.
        """
        runs.append(str(user_id))
        await asyncio.sleep(0.05)

    await asyncio.gather(
        run_for_each_user(user_ids, run, lock, lock_name="automation", limits=LIMITS),
        run_for_each_user(user_ids, run, lock, lock_name="automation", limits=LIMITS),
    )

    assert sorted(runs) == sorted(str(user_id) for user_id in user_ids)


async def test_lock_refuses_a_second_holder_while_leased() -> None:
    """A second holder is told the lease is busy instead of waiting.

    Returns:
        None.
    """
    lock = make_lock()
    async with lock.acquire("automation:solo", ttl_sec=TTL_SEC, refresh_sec=REFRESH_SEC):
        with pytest.raises(LockBusyError):
            async with lock.acquire("automation:solo", ttl_sec=TTL_SEC, refresh_sec=REFRESH_SEC):
                pytest.fail("the second holder must not get the lease")


async def test_lease_loss_stops_the_work_before_its_next_step() -> None:
    """A lease taken away mid-work interrupts the holder instead of letting it run.

    Returns:
        None.
    """
    redis = aioredis.FakeRedis(decode_responses=True)
    lock = RedisDistributedLock(redis, key_prefix=PREFIX, io_timeout_sec=IO_TIMEOUT_SEC)
    reached_commands = False

    async def work() -> None:
        """Lose the lease while sleeping, then try to reach the board."""
        nonlocal reached_commands
        async with lock.acquire(
            "automation:solo",
            ttl_sec=SHORT_TTL_SEC,
            refresh_sec=SHORT_REFRESH_SEC,
        ):
            await redis.delete(keys.lock_key(PREFIX, "automation:solo"))
            await asyncio.sleep(SHORT_TTL_SEC)
            reached_commands = True

    with pytest.raises(LeaseLostError):
        await asyncio.wait_for(work(), timeout=SHORT_TTL_SEC * 3)

    assert reached_commands is False
