"""Окружение Alembic для базы бэкенда.

Ревизии идут по тому же асинхронному движку, которым пользуется приложение, а
метаданные, с которыми они сверяются, — это объявления таблиц слоя хранения. Именно
поэтому ``alembic revision --autogenerate`` способен показать колонку, которая
появилась в модели, но не появилась в ревизии.

Адрес базы берётся из ``DATABASE_URL``, если окружение его задало: тогда развёртывание
мигрирует ту базу, с которой действительно работает, а не адрес, записанный в файл
конфигурации в момент его создания. Пакет ``backend`` берётся из ``src``: путь к нему
добавляет сам Alembic из ``prepend_sys_path`` в ``alembic.ini``, поэтому этот файл не
правит ``sys.path`` вручную и не зависит от того, откуда его запустили.
"""

from __future__ import annotations

import asyncio
import os
from logging.config import fileConfig

from alembic import context
from sqlalchemy import Connection, pool
from sqlalchemy.ext.asyncio import async_engine_from_config

from backend.infrastructure.database.models import Base

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def database_url() -> str:
    """Возвращает адрес базы, по которой должны пройти ревизии.

    Returns:
        str: Адрес подключения: из окружения, если оно его задало, иначе из файла
            конфигурации.
    """
    return os.environ.get("DATABASE_URL") or config.get_main_option("sqlalchemy.url")


def run_migrations_offline() -> None:
    """Выводит SQL ревизий, ни к чему не подключаясь.

    Returns:
        None.
    """
    context.configure(
        url=database_url(),
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_on(connection: Connection) -> None:
    """Проводит ревизии по одному открытому соединению.

    Args:
        connection: Соединение, на котором выполняются ревизии.

    Returns:
        None.
    """
    context.configure(
        connection=connection,
        target_metadata=target_metadata,
        compare_type=True,
    )
    with context.begin_transaction():
        context.run_migrations()


async def migrate() -> None:
    """Открывает движок и проводит все ожидающие ревизии.

    Returns:
        None.
    """
    engine = async_engine_from_config(
        {"sqlalchemy.url": database_url()},
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    try:
        async with engine.connect() as connection:
            await connection.run_sync(run_migrations_on)
    finally:
        await engine.dispose()


def run_migrations_online() -> None:
    """Проводит ревизии по настоящей базе.

    Returns:
        None.
    """
    asyncio.run(migrate())


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
