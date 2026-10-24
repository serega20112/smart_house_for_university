"""Хранилище опорных фраз классификатора намерений.

Классификатор сравнивает предложение с таблицей фраз, а не со списком в памяти
процесса: индекс один на несколько воркеров, фразу можно добавить без развёртывания,
и поиск ближайших соседей идёт внутри Postgres там, где уже лежат векторы.

Таблица зарегистрирована в метаданных уровня постоянства, поэтому ревизия,
сгенерированная ``alembic revision --autogenerate``, видит её как любую другую
таблицу: достаточно, что пакет таблиц импортирует этот модуль.
"""

from __future__ import annotations

from pgvector.sqlalchemy import Vector
from sqlalchemy import Column, Index, String, Table, UniqueConstraint

from backend.infrastructure.database.models.base import Base

TABLE_NAME = "reference_phrases"
COLUMN_ID = "id"
COLUMN_INTENT = "intent"
COLUMN_PHRASE = "phrase"
COLUMN_EMBEDDING = "embedding"

EMBEDDING_DIMENSIONS = 384
INTENT_WIDTH = 32
PHRASE_WIDTH = 200
IDENTIFIER_LENGTH = 36

NEAREST_LABEL = "distance"

REFERENCE_PHRASES = Table(
    TABLE_NAME,
    Base.metadata,
    Column(COLUMN_ID, String(IDENTIFIER_LENGTH), primary_key=True),
    Column(COLUMN_INTENT, String(INTENT_WIDTH), nullable=False),
    Column(COLUMN_PHRASE, String(PHRASE_WIDTH), nullable=False),
    Column(COLUMN_EMBEDDING, Vector(EMBEDDING_DIMENSIONS), nullable=True),
    UniqueConstraint(COLUMN_INTENT, COLUMN_PHRASE, name="uq_reference_phrases_intent_phrase"),
    Index("ix_reference_phrases_intent", COLUMN_INTENT),
)

__all__ = [
    "COLUMN_EMBEDDING",
    "COLUMN_ID",
    "COLUMN_INTENT",
    "COLUMN_PHRASE",
    "EMBEDDING_DIMENSIONS",
    "IDENTIFIER_LENGTH",
    "INTENT_WIDTH",
    "NEAREST_LABEL",
    "PHRASE_WIDTH",
    "REFERENCE_PHRASES",
    "TABLE_NAME",
]
