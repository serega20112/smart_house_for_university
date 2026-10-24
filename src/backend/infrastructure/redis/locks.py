"""Аренда, о которой договариваются несколько процессов-воркеров.

Решение «этот дом уже автоматизируют» не может жить внутри одного процесса: два воркера
ARQ могут взять один и тот же период одновременно. Аренда — ключ Redis со случайным
токеном: кто первый записал его через SET NX, тот и владеет; цикл продления удлиняет
аренду, пока держатель работает, а Lua-скрипт делает и продление, и освобождение
условными по токену, поэтому медленный держатель не сможет ни продлить, ни удалить
аренду того, кто пришёл ему на смену после истечения срока.
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
    """Аренда, которую держит ровно один процесс, с продлением во время работы.

    Attributes:
        redis: Соединение, в котором живёт ключ аренды.
        key_prefix: Пространство имён, отделяющее развёртывания на одном сервере.
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
        """Забирает аренду и удлиняет её до конца блока.

        Аренду берут через SET NX, поэтому выиграть может только один вызов; проигравшим
        говорят сразу, вместо того чтобы их ждать, — а вызывающий сам решает, значит ли
        это «пропустить этот круг». Пока блок идёт, задача продления удлиняет аренду, чтобы
        долгая работа не отдала её соседу.

        Args:
            key: Имя блокировки.
            ttl_sec: Изначальное время жизни в секундах.
            refresh_sec: Как часто продлевать аренду.

        Yields:
            None: Пока вызывающий работает, блокировка удерживается.

        Raises:
            TimeoutError: Когда аренду сейчас держит другой.
            ValueError: Когда период продления не короче самой аренды — тогда она будет
                истекать между двумя продлениями.
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
        """Удлиняет аренду каждый период, пока держатель работает.

        Args:
            name: Полный ключ аренды.
            token: Секрет, называющий держателя.
            ttl_sec: Длина аренды, которую ставят заново при каждом продлении.
            refresh_sec: Секунд между двумя продлениями.
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
        """Удаляет аренду, только если её всё ещё держит этот владелец.

        Args:
            name: Полный ключ аренды.
            token: Секрет, называющий держателя.
        """
        try:
            async with asyncio.timeout(IO_TIMEOUT_SECONDS):
                await self._eval(_RELEASE_SCRIPT, name, token)
        except Exception:
            log.exception("locks.release_failed", key=name)

    async def _eval(self, script: str, name: str, *args: str) -> str:
        """Запускает Lua-скрипт по ключу аренды, с таймаутом на ввод-вывод.

        Args:
            script: Текст на Lua, решающий, что делает сервер.
            name: Полный ключ аренды.
            args: Аргументы скрипта: токен держателя и длины аренды.

        Returns:
            Ответ сервера в сыром виде.
        """
        response: Awaitable[str] | str = self._redis.eval(script, 1, name, *args)
        if isinstance(response, str):
            return response
        return await response
