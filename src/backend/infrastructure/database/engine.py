"""Фабрики движка и сессий хранилища.

Движок создаёт один раз композиционный корень, и он уходит всем, кому нужен, поэтому пул
соединений общий, а не собираемый на каждый запрос. Сессию здесь не открывают ни одну:
сессия принадлежит границе транзакции, и только она решает, когда транзакция кончается.

Схему отсюда не создают никогда. Применять ревизии Alembic — шаг развёртывания, поэтому
таблицы работающей системы остаются осознанным решением, а не побочным эффектом импорта
модуля.
"""

from __future__ import annotations

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)


def build_engine(
    url: str,
    *,
    echo: bool = False,
    pool_size: int = 10,
    pool_max_overflow: int = 10,
    pool_recycle_sec: int = 1800,
) -> AsyncEngine:
    """Создаёт асинхронный движок по адресу подключения.

    Соединения проверяют прежде, чем отдать, и меняют по истечении настроенного срока
    жизни: плата держит долгий сокет открытым, а база вольна сбросить соединение, которое
    никто не трогал.

    Args:
        url: Асинхронный адрес подключения SQLAlchemy, на драйвере asyncpg.
        echo: Писать ли в журнал всякий запрос.
        pool_size: Число держаемых открытыми соединений.
        pool_max_overflow: Добавочные соединения, когда пул занят.
        pool_recycle_sec: Возраст, после которого соединение меняют.

    Returns:
        AsyncEngine: Настроенный движок.
    """
    return create_async_engine(
        url,
        echo=echo,
        pool_pre_ping=True,
        pool_size=pool_size,
        max_overflow=pool_max_overflow,
        pool_recycle=pool_recycle_sec,
    )


def build_session_factory(engine: AsyncEngine) -> async_sessionmaker[AsyncSession]:
    """Создаёт фабрику сессий, из которой границы транзакции берут свои сессии.

    Объекты не сбрасываются после коммита транзакции: агрегаты, которые сценарий
    приложения держит после своего блока, — уже простые значения домена, а ленивое
    обновление потребовало бы закрытую к тому моменту сессию.

    Args:
        engine: Движок, к которому привязывают сессии.

    Returns:
        async_sessionmaker[AsyncSession]: Фабрика сессий.
    """
    return async_sessionmaker(engine, expire_on_commit=False)
