"""Границы транзакций сохраняют только по явному `commit()` и откатывают при ошибке.

Эти проверки фиксируют осознанный отказ от неявного коммита (п. 4.2 ТЗ): чистый выход из
блока ничего не сохраняет, сохраняет лишь вызов `commit()`, а любое исключение откатывает.
Фейковая сессия считает вызовы `commit`/`rollback`/`close`, поэтому логика проверяется
детерминированно и без сервера — ровно тот жизненный цикл, что даёт настоящая граница.
"""

from __future__ import annotations

import pytest

from backend.application.interfaces.unit_of_work.transaction import TransactionalUnitOfWork
from backend.infrastructure.database.unit_of_work import SqlUnitOfWork


class _FakeTransaction:
    """Транзакция, помечающая, чем её закончили."""

    def __init__(self) -> None:
        self.committed = False
        self.rolled_back = False

    async def commit(self) -> None:
        self.committed = True

    async def rollback(self) -> None:
        self.rolled_back = True


class _FakeSession:
    """Сессия, отдающая одну и ту же фейковую транзакцию и считающая закрытие."""

    def __init__(self) -> None:
        self.transaction = _FakeTransaction()
        self.closed = False

    async def begin(self) -> _FakeTransaction:
        return self.transaction

    async def close(self) -> None:
        self.closed = True


class _RecordingUnitOfWork(TransactionalUnitOfWork):
    """Минимальная конкретная граница поверх общего протокола."""

    def __init__(self) -> None:
        self.commits = 0
        self.rollbacks = 0

    async def commit(self) -> None:
        self.commits += 1

    async def rollback(self) -> None:
        self.rollbacks += 1


def _uow_over(session: _FakeSession) -> SqlUnitOfWork:
    """Строит SQL-границу поверх одной заранее созданной фейковой сессии.

    Args:
        session: Фейковая сессия, которую должна использовать граница.

    Returns:
        SqlUnitOfWork: Граница, чьё жизненное кольцо надо проверить.
    """

    def factory() -> _FakeSession:
        return session

    return SqlUnitOfWork(factory)


async def test_clean_exit_does_not_commit() -> None:
    """Успешный выход из блока не фиксирует изменения сам по себе."""
    session = _FakeSession()

    async with _uow_over(session):
        pass

    assert not session.transaction.committed
    assert not session.transaction.rolled_back
    assert session.closed


async def test_explicit_commit_saves() -> None:
    """Явный `commit()` внутри блока сохраняет транзакцию ровно один раз."""
    session = _FakeSession()

    async with _uow_over(session) as uow:
        await uow.commit()

    assert session.transaction.committed
    assert session.closed


async def test_exception_rolls_back() -> None:
    """Исключение внутри блока откатывает транзакцию и продолжается наружу."""
    session = _FakeSession()

    with pytest.raises(ValueError, match="boom"):
        async with _uow_over(session):
            raise ValueError("boom")

    assert session.transaction.rolled_back
    assert not session.transaction.committed
    assert session.closed


async def test_base_protocol_commits_only_when_asked() -> None:
    """Общий протокол: чистый выход не коммитит, ошибка — откатывает."""
    success = _RecordingUnitOfWork()
    async with success:
        pass
    assert success.commits == 0
    assert success.rollbacks == 0

    failed = _RecordingUnitOfWork()
    with pytest.raises(KeyError):
        async with failed:
            await failed.commit()
            raise KeyError("nope")
    assert failed.commits == 1
    assert failed.rollbacks == 1
