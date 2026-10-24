"""Общее поведение любой границы транзакции.

Протокол транзакции описан здесь один раз: войти в блок, commit, если ничего не
взлетело, rollback, если взлетело. Конкретные границы не добавляют ничего, кроме
репозиториев, которые они отдают, — поэтому три маленьких класса вместо трёх
копий одного и того же жизненного цикла.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from types import TracebackType
from typing import Self


class TransactionalUnitOfWork(ABC):
    """Блок работы, который заканчивается ровно одним commit или одним rollback."""

    async def __aenter__(self) -> Self:
        """Открывает транзакцию."""
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> None:
        """Коммитит при успехе и откатывает при ошибке.

        Блок никогда не глотает исключение: он решает лишь, чем закончится
        транзакция, а исключение продолжает распространяться.

        Args:
            exc_type: Тип поднятого исключения или None.
            exc_val: Само исключение или None.
            exc_tb: Его traceback или None.
        """
        if exc_type is None:
            await self.commit()
        else:
            await self.rollback()

    @abstractmethod
    async def commit(self) -> None:
        """Атомарно сохраняет всё сделанное внутри блока."""

    @abstractmethod
    async def rollback(self) -> None:
        """Отбрасывает всё сделанное внутри блока."""
