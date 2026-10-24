"""Аренда, о которой договариваются несколько процессов-воркеров.

Решение «этот дом уже автоматизируют» не может жить внутри одного процесса: два воркера
ARQ могут взять один и тот же период одновременно. Аренда — ключ Redis со случайным
токеном: кто первый записал его через SET NX, тот и владеет; цикл продления удлиняет
аренду, пока держатель работает, а Lua-скрипт делает и продление, и освобождение
условными по токену, поэтому медленный держатель не сможет ни продлить, ни удалить
аренду того, кто пришёл ему на смену после истечения срока.

Потерянная аренда не оставляет работу «просто идти дальше»: хранилище могло не ответить
или ключ успел истечь, и тогда тот же дом взял сосед. Держащая задача отменяется, а
блок получает :class:`LeaseLostError` — работа, которую уже выполняет кто-то другой, не
должна доходить до команд.
"""

from __future__ import annotations

import asyncio
import uuid
from collections.abc import AsyncIterator, Awaitable
from contextlib import asynccontextmanager, suppress
from typing import Any, Final

from redis.asyncio import Redis

from backend.application.interfaces.services.system.distributed_lock import (
    DistributedLock,
    LeaseLostError,
    LockBusyError,
    LockUnavailableError,
)
from backend.infrastructure.brokers import keys
from backend.infrastructure.system.logging import get_logger

log = get_logger("locks")

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
        io_timeout_sec: Сколько ждать ответа хранилища на одну команду.
    """

    def __init__(self, redis: Redis, *, key_prefix: str, io_timeout_sec: float) -> None:
        """Инициализирует аренду.

        Args:
            redis: Соединение, в котором живёт ключ аренды.
            key_prefix: Пространство имён, отделяющее одно развёртывание от другого.
            io_timeout_sec: Сколько ждать ответа хранилища на одну команду: молчащий
                Redis должен стать отказом, а не бесконечным ожиданием.
        """
        self._redis = redis
        self._key_prefix = key_prefix
        self._io_timeout_sec = io_timeout_sec

    @asynccontextmanager
    async def acquire(self, key: str, *, ttl_sec: int, refresh_sec: int) -> AsyncIterator[None]:
        """Забирает аренду и удлиняет её до конца блока.

        Аренду берут через SET NX, поэтому выиграть может только один вызов; проигравшим
        говорят сразу, вместо того чтобы их ждать, — а вызывающий сам решает, значит ли
        это «пропустить этот круг». Пока блок идёт, задача продления удлиняет аренду, чтобы
        долгая работа не отдала её соседу; если продлить не удалось, блок прерывается.

        Args:
            key: Имя блокировки.
            ttl_sec: Изначальное время жизни в секундах.
            refresh_sec: Как часто продлевать аренду.

        Yields:
            None: Пока вызывающий работает, блокировка удерживается.

        Raises:
            LockBusyError: Когда аренду сейчас держит другой.
            LockUnavailableError: Когда хранилище не ответило на попытку взять аренду.
            LeaseLostError: Когда аренда потеряна уже во время работы.
            ValueError: Когда период продления не короче самой аренды — тогда она будет
                истекать между двумя продлениями.
        """
        if refresh_sec >= ttl_sec:
            raise ValueError("refresh_sec must be shorter than ttl_sec")
        name = keys.lock_key(self._key_prefix, key)
        token = uuid.uuid4().hex
        try:
            async with asyncio.timeout(self._io_timeout_sec):
                won = await self._redis.set(name, token, nx=True, px=ttl_sec * 1000)
        except TimeoutError as error:
            raise LockUnavailableError(f"lock {key} was not answered in time") from error
        if not won:
            raise LockBusyError(f"lock {key} is held by another worker")
        holder = asyncio.current_task()
        lost = asyncio.Event()
        renewal = asyncio.create_task(self._renew(name, token, ttl_sec, refresh_sec, holder, lost))
        try:
            yield
        except asyncio.CancelledError:
            if lost.is_set():
                raise LeaseLostError(f"lock {key} was lost while its work was running") from None
            raise
        finally:
            renewal.cancel()
            with suppress(asyncio.CancelledError):
                await renewal
            await self._release(name, token)

    async def _renew(
        self,
        name: str,
        token: str,
        ttl_sec: int,
        refresh_sec: int,
        holder: asyncio.Task[Any] | None,
        lost: asyncio.Event,
    ) -> None:
        """Удлиняет аренду каждый период, а при неудаче прерывает держателя.

        Отказ хранилища и потерянная аренда — равнозначно плохие новости для
        вызывающего: в обоих случаях ключ больше не принадлежит этой задаче, и
        продолжать работу значит делить её с тем, кого уже пустили вместо него.
        Поэтому держатель отменяется, а контекст превращает отмену в
        :class:`LeaseLostError`.

        Args:
            name: Полный ключ аренды.
            token: Секрет, называющий держателя.
            ttl_sec: Длина аренды, которую ставят заново при каждом продлении.
            refresh_sec: Секунд между двумя продлениями.
            holder: Задача, выполняющая блок и подлежащая отмене.
            lost: Отметка о том, что держать аренду больше нельзя.
        """
        while True:
            await asyncio.sleep(refresh_sec)
            try:
                async with asyncio.timeout(self._io_timeout_sec):
                    renewed = await self._eval(_RENEW_SCRIPT, name, token, str(ttl_sec))
            except Exception:
                log.exception("locks.renew_failed", key=name)
                self._abandon(holder, lost)
                return
            if not renewed:
                log.warning("locks.lease_lost", key=name)
                self._abandon(holder, lost)
                return

    @staticmethod
    def _abandon(holder: asyncio.Task[Any] | None, lost: asyncio.Event) -> None:
        """Отмечает потерю аренды и отменяет работу, которая её держала.

        Args:
            holder: Задача, выполняющая блок, либо None вне запущенной задачи.
            lost: Отметка, по которой контекст отличит потерю от чужой отмены.
        """
        lost.set()
        if holder is not None:
            holder.cancel()

    async def _release(self, name: str, token: str) -> None:
        """Удаляет аренду, только если её всё ещё держит этот владелец.

        Args:
            name: Полный ключ аренды.
            token: Секрет, называющий держателя.
        """
        try:
            async with asyncio.timeout(self._io_timeout_sec):
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
