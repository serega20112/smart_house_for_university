"""Блокировка, живущая во внешнем хранилище."""

from __future__ import annotations

from abc import ABC, abstractmethod
from contextlib import AbstractAsyncContextManager


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
            TimeoutError: Когда блокировку не удалось взять.
        """
