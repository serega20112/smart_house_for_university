"""Регистрация аккаунта проходит через SQL-маппер и через реальную базу.

Этот файл ловит дефект P0-1: маппер аккаунта знал колонку `version`, которой нет ни у
агрегата `User`, ни у таблицы `users`, из-за чего первая же регистрация падала на
`AttributeError` ещё до обращения к хранилищу. Первые проверки держат контракт
«агрегат <-> строка <-> схема» без сервера; последние идут к настоящей PostgreSQL (если
она поднята) и проверяют запись, чтение и конфликт уникального логина целиком.
"""

from __future__ import annotations

from datetime import UTC, datetime

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from backend.application.errors import EmailAlreadyTakenError
from backend.domain.aggregates.user.user import User
from backend.domain.value_objects.account.display_name import DisplayName
from backend.domain.value_objects.account.email import Email
from backend.infrastructure.database.mappers import row_values, user_from_row, user_to_row
from backend.infrastructure.database.models import UserModel
from backend.infrastructure.database.repositories.account_repository import SqlAccountRepository

CREATED_AT = datetime(2027, 1, 1, 12, 0, tzinfo=UTC)


def make_user() -> User:
    """Строит зарегистрированный аккаунт.

    Returns:
        User: Аккаунт с заведомо валидными логином, именем и паролем.
    """
    return User.register(
        email=Email.parse("ivan@example.com"),
        display_name=DisplayName.parse("Ivan Petrov"),
        password_hash="hashed-secret-value",
        created_at=CREATED_AT,
    )


def test_account_is_not_versioned_by_schema():
    """Таблица аккаунтов не имеет колонки версии — осознанное решение.

    Returns:
        None: Только проверка схемы.
    """
    assert "version" not in {column.name for column in UserModel.__table__.columns}


def test_registration_maps_to_row_without_stray_columns():
    """Агрегат разглаживается ровно в те колонки, что есть у таблицы.

    Returns:
        None: Только проверка значений.
    """
    user = make_user()
    row = user_to_row(user)
    columns = {column.name for column in UserModel.__table__.columns}

    assert set(row_values(UserModel.__table__, row)) == columns
    assert row.id == user.id.value
    assert row.email == "ivan@example.com"
    assert row.display_name == "Ivan Petrov"
    assert row.password_hash == "hashed-secret-value"
    assert row.created_at == CREATED_AT


def test_registration_round_trip_restores_the_aggregate():
    """Сохранённый аккаунт читается обратно равным исходному.

    Returns:
        None: Только проверка равенства.
    """
    user = make_user()

    assert user_from_row(user_to_row(user)) == user


async def test_registration_writes_and_reads_on_real_postgres(sql_session: AsyncSession) -> None:
    """Новый аккаунт записывается и читается через SQL-репозиторий на живой базе.

    Args:
        sql_session: Сессия с откатываемой транзакцией (или пропуск без базы).

    Returns:
        None: Только проверка сквозного прохода записи и чтения.
    """
    user = make_user()
    repository = SqlAccountRepository(sql_session)

    await repository.add(user)
    loaded = await repository.get(user.id)

    assert loaded == user


async def test_duplicate_email_is_rejected_on_real_postgres(sql_session: AsyncSession) -> None:
    """Повторный логин отвергается хранилищем, а не тихо перезаписывается.

    Args:
        sql_session: Сессия с откатываемой транзакцией (или пропуск без базы).

    Returns:
        None: Только проверка отказа на уникальный конфликт.
    """
    repository = SqlAccountRepository(sql_session)
    await repository.add(make_user())

    with pytest.raises(EmailAlreadyTakenError):
        await repository.add(make_user())
