"""База объявления, против которой описана каждая таблица.

Декларативное описание всех таблиц реляционного хранилища.
"""

from __future__ import annotations

from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    """Declarative base every table of the store is declared against."""
