"""Alembic environment of the smart home backend.

The revisions run against the same async engine the application uses, and the
metadata they are compared against is the one declared by the table definitions
of the persistence layer. That is what lets ``alembic revision --autogenerate``
report a column that was added to a model but never to a revision.

The database address comes from ``DATABASE_URL`` when the environment provides
one, so a deployment migrates the database it actually runs against instead of
the address written into a configuration file at the time the file was created.
"""

from __future__ import annotations

import asyncio
import os
from logging.config import fileConfig

from alembic import context
from sqlalchemy import Connection, pool
from sqlalchemy.ext.asyncio import async_engine_from_config

from backend.infrastructure.database.tables import Base

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def database_url() -> str:
    """Return the address of the database the revisions have to run against.

    Returns:
        str: Connection URL, taken from the environment when it is set and from
        the configuration file otherwise.
    """
    return os.environ.get("DATABASE_URL") or config.get_main_option("sqlalchemy.url")


def run_migrations_offline() -> None:
    """Emit the SQL of the revisions without connecting to anything.

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
    """Run the revisions against one open connection.

    Args:
        connection: Connection the revisions are executed on.

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
    """Open the engine and run every pending revision.

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
    """Run the revisions against a real database.

    Returns:
        None.
    """
    asyncio.run(migrate())


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
