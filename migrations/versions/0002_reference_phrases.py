"""Опорные фразы классификатора намерений.

Классификатор держал опорные фразы списком внутри процесса: каждый рабочий
индексировал одни и те же данные отдельно, а новая формулировка требовала
развёртывания. Фразы становятся строками: вектор считается один раз, а поиск идёт
по косинусному расстоянию через граф HNSW, то есть индекс живёт там, где
происходит поиск по векторам.

Расширение создаётся здесь, а не в заметке о развёртывании, потому что без него
нет самого типа колонки, а ревизия, которая не может пройти на чистой базе, — не
ревизия.

Revision ID: 0002_reference_phrases
Revises: 0001_initial
Created: 2026-01-02 00:00:00.000000

"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from pgvector.sqlalchemy import Vector

revision: str = "0002_reference_phrases"
down_revision: str | None = "0001_initial"
branch_labels: str | None = None
depends_on: str | None = None

TABLE_NAME = "reference_phrases"
COLUMN_ID = "id"
COLUMN_INTENT = "intent"
COLUMN_PHRASE = "phrase"
COLUMN_EMBEDDING = "embedding"
IDENTIFIER_LENGTH = 36
INTENT_WIDTH = 32
PHRASE_WIDTH = 200
EMBEDDING_DIMENSIONS = 384

UNIQUE_CONSTRAINT = "uq_reference_phrases_intent_phrase"
INTENT_INDEX = "ix_reference_phrases_intent"
EMBEDDING_INDEX = "ix_reference_phrases_embedding_hnsw"
PRIMARY_KEY = "pk_reference_phrases"


def upgrade() -> None:
    """Создаёт таблицу опорных фраз и индекс по векторам.

    Returns:
        None.
    """
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")
    op.create_table(
        TABLE_NAME,
        sa.Column(COLUMN_ID, sa.String(length=IDENTIFIER_LENGTH), nullable=False),
        sa.Column(COLUMN_INTENT, sa.String(length=INTENT_WIDTH), nullable=False),
        sa.Column(COLUMN_PHRASE, sa.String(length=PHRASE_WIDTH), nullable=False),
        sa.Column(COLUMN_EMBEDDING, Vector(EMBEDDING_DIMENSIONS), nullable=True),
        sa.PrimaryKeyConstraint(COLUMN_ID, name=PRIMARY_KEY),
        sa.UniqueConstraint(COLUMN_INTENT, COLUMN_PHRASE, name=UNIQUE_CONSTRAINT),
    )
    op.create_index(INTENT_INDEX, TABLE_NAME, [COLUMN_INTENT])
    op.execute(
        f"CREATE INDEX {EMBEDDING_INDEX} ON {TABLE_NAME} "
        f"USING hnsw ({COLUMN_EMBEDDING} vector_cosine_ops)"
    )


def downgrade() -> None:
    """Удаляет таблицу опорных фраз и индекс по векторам.

    Returns:
        None.
    """
    op.execute(f"DROP INDEX IF EXISTS {EMBEDDING_INDEX}")
    op.drop_index(INTENT_INDEX, table_name=TABLE_NAME)
    op.drop_table(TABLE_NAME)
