"""Reference phrases of the intent classifier.

The classifier used to hold its reference phrases in a list inside the process,
which meant every worker indexed the same data separately and a new phrasing
needed a deployment. The phrases become rows instead, embedded once and searched
by cosine distance through an HNSW graph, so the index lives in the store where
the vector search actually happens.

The extension is created here rather than in a deployment note because the column
type does not exist without it, and a revision that cannot run on a fresh
database is not a revision.

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
    """Create the reference phrase table and its vector index.

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
    """Remove the reference phrase table and its vector index.

    Returns:
        None.
    """
    op.execute(f"DROP INDEX IF EXISTS {EMBEDDING_INDEX}")
    op.drop_index(INTENT_INDEX, table_name=TABLE_NAME)
    op.drop_table(TABLE_NAME)
