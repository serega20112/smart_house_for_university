"""Блокировка, живущая во внешнем хранилище."""

from __future__ import annotations

from abc import ABC, abstractmethod
from contextlib import AbstractAsyncContextManager


class LockBusyError(Exception):
    """Аренду сейчас держит другой процесс — этот круг работы не нужен."""


class LockUnavailableError(Exception):
    """Хранилище аренд не ответило: взять или продлить аренду не удалось."""


class LeaseLostError(Exception):
    """Аренда потеряна во время работы — продолжать её нельзя без дублирования."""


class DistributedLock(ABC):
    """Не даёт двум рабочим сделать одну и ту же работу."""

    @abstractmethod
    def acquire(
        self,
        key: str,
        *,
        ttl_sec: int,
        refresh_sec: int,
    ) -> AbstractAsyncContextManager[None]:
        """Берёт блокировку и продлевает аренду до конца блока.

        Args:
            key: Имя блокировки.
            ttl_sec: Изначальное время жизни в секундах.
            refresh_sec: Как часто аренду продлевают.

        Returns:
            AbstractAsyncContextManager: Контекст, держащий аренду.

        Raises:
            LockBusyError: Когда аренду держит другой процесс.
            LockUnavailableError: Когда хранилище аренд не ответило.
            LeaseLostError: Когда аренда истекла, пока блок выполнялся: работа
                уже не одинока, и продолжать её значит дублировать команды.
        """
