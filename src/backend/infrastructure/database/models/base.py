"""База объявления, против которой описана каждая таблица.

Декларативное описание всех таблиц реляционного хранилища.
"""

from __future__ import annotations

from typing import ClassVar

from sqlalchemy import Table
from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    """База объявления, против которой описана каждая таблица хранилища.

    Атрибут `__table__` объявлен явно как `Table`: каждый класс таблицы в рантайме им и
    является, а явная аннотация освобождает вызывающих от развода типов между `Table` и
    широким `FromClause` там, где хранилище пишет запрос именно по таблице.

    Attributes:
        __table__: Таблица SQLAlchemy, описанная этим классом.
    """

    __table__: ClassVar[Table]
