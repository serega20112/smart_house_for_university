"""Общее поведение любой границы транзакции.

Протокол транзакции описан здесь один раз: войти в блок, откатить, если что-то взлетело,
и отпустить соединение в конце. Фиксирует изменения только явный `commit()`: успешный
выход из блока сам по себе ничего не сохраняет. Это осознанный отказ от неявного
коммита — «сохрани всё изменённое» прячет момент сохранения, а явный `commit()` делает
границу записи видимой и проверяемой тестом.

Конкретные границы не добавляют ничего, кроме репозиториев, которые они отдают, —
поэтому три маленьких класса вместо трёх копий одного и того же жизненного цикла.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from types import TracebackType
from typing import Self


class TransactionalUnitOfWork(ABC):
    """Блок работы: откат при ошибке, иначе — сохранение только явным `commit()`."""

    async def __aenter__(self) -> Self:
        """Открывает транзакцию."""
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> None:
        """Откатывает при ошибке и отпускает ресурсы, но не коммитит молча.

        Сохраняет только вызов `commit()` внутри блока; без него изменения не уходят в
        базу. Исключение, если оно было, откатывает транзакцию и продолжается дальше.

        Args:
            exc_type: Тип поднятого исключения или None.
            exc_val: Само исключение или None.
            exc_tb: Его traceback или None.
        """
        if exc_type is not None:
            await self.rollback()

    @abstractmethod
    async def commit(self) -> None:
        """Атомарно сохраняет всё сделанное внутри блока."""

    @abstractmethod
    async def rollback(self) -> None:
        """Отбрасывает всё сделанное внутри блока."""
