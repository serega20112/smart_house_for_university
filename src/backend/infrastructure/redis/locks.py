"""A lease several worker processes can agree on.

The decision "is this home already being automated" cannot live inside one
process: two ARQ workers may pick up the same period at the same moment. The
lease is a Redis key holding a random token. Whoever writes it with SET NX
first owns it, a renewal loop extends the lease while the holder works, and a
Lua script makes both renewal and release conditional on the token, so a slow
holder can never prolong or delete the lease of the one that took over after
the expiry.
"""

from __future__ import annotations

import asyncio
import uuid
from collections.abc import AsyncIterator, Awaitable
from contextlib import asynccontextmanager, suppress
from typing import Final

from redis.asyncio import Redis

from backend.application.interface.services.distributed_lock import DistributedLock
from backend.infrastructure.logging import get_logger
from backend.infrastructure.redis import keys

log = get_logger("locks")

IO_TIMEOUT_SECONDS: Final = 5

_RENEW_SCRIPT: Final = """\
if redis.call('GET', KEYS[1]) == ARGV[1] then
    return redis.call('EXPIRE', KEYS[1], ARGV[2])
end
return 0
"""

_RELEASE_SCRIPT: Final = """\
if redis.call('GET', KEYS[1]) == ARGV[1] then
    return redis.call('DEL', KEYS[1])
end
return 0
"""


class RedisDistributedLock(DistributedLock):
    """Lease held by exactly one process at a time, renewed while it works.

    Args:
        redis: Connection the lease key lives in.
        key_prefix: Namespace separating deployments that share one server.
    """

    def __init__(self, redis: Redis, *, key_prefix: str) -> None:
        """Инициализирует аренду.

        Args:
            redis: Соединение, в котором живёт ключ аренды.
            key_prefix: Пространство имён, отделяющее одно развёртывание от другого.
        """
        self._redis = redis
        self._key_prefix = key_prefix

    @asynccontextmanager
    async def acquire(self, key: str, *, ttl_sec: int, refresh_sec: int) -> AsyncIterator[None]:
        """Acquire the lease, extending it until the block ends.

        The lease is taken with SET NX, so only one caller can win; the losers
        are told immediately instead of waiting, and the caller decides whether
        that means "skip this round". While the block runs, a renewal task
        keeps extending the lease so a long job does not lose it to a peer.

        Args:
            key: Name of the lock.
            ttl_sec: Initial time-to-live in seconds.
            refresh_sec: How often the lease is extended.

        Yields:
            None: The lock is held while the caller runs.

        Raises:
            TimeoutError: When another holder owns the lease right now.
            ValueError: When the renewal period is not shorter than the lease,
                which would let the lease expire between two renewals.
        """
        if refresh_sec >= ttl_sec:
            raise ValueError("refresh_sec must be shorter than ttl_sec")
        name = keys.lock_key(self._key_prefix, key)
        token = uuid.uuid4().hex
        async with asyncio.timeout(IO_TIMEOUT_SECONDS):
            won = await self._redis.set(name, token, nx=True, px=ttl_sec * 1000)
        if not won:
            raise TimeoutError(f"lock {key} is held by another worker")
        renewal = asyncio.create_task(self._renew(name, token, ttl_sec, refresh_sec))
        try:
            yield
        finally:
            renewal.cancel()
            with suppress(asyncio.CancelledError):
                await renewal
            await self._release(name, token)

    async def _renew(self, name: str, token: str, ttl_sec: int, refresh_sec: int) -> None:
        """Extend the lease every period while the holder is working.

        Args:
            name: Full key of the lease.
            token: Secret identifying the holder.
            ttl_sec: Lease length to reset on every renewal.
            refresh_sec: Seconds between two renewals.
        """
        while True:
            await asyncio.sleep(refresh_sec)
            try:
                async with asyncio.timeout(IO_TIMEOUT_SECONDS):
                    renewed = await self._eval(_RENEW_SCRIPT, name, token, str(ttl_sec))
            except Exception:
                log.exception("locks.renew_failed", key=name)
                return
            if not renewed:
                log.warning("locks.lease_lost", key=name)
                return

    async def _release(self, name: str, token: str) -> None:
        """Delete the lease if, and only if, this holder still owns it.

        Args:
            name: Full key of the lease.
            token: Secret identifying the holder.
        """
        try:
            async with asyncio.timeout(IO_TIMEOUT_SECONDS):
                await self._eval(_RELEASE_SCRIPT, name, token)
        except Exception:
            log.exception("locks.release_failed", key=name)

    async def _eval(self, script: str, name: str, *args: str) -> str:
        """Run a Lua script against the lease key, under an IO timeout.

        Args:
            script: Lua source deciding what the server does.
            name: Full key of the lease.
            args: Script arguments, the holder token and lease lengths.

        Returns:
            Raw answer of the server.
        """
        response: Awaitable[str] | str = self._redis.eval(script, 1, name, *args)
        if isinstance(response, str):
            return response
        return await response
