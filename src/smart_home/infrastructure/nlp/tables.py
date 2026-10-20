"""Storage of the reference phrases of the intent classifier.

The classifier matches a sentence against a table of phrases rather than against
a list held in memory, so several workers share one index, a phrase can be added
without a deployment, and the nearest neighbour search runs inside Postgres
where the vectors already live.

The table is registered on the metadata of the persistence layer, so a revision
generated with ``alembic revision --autogenerate`` sees it like any other table.
Importing this module is therefore enough for the comparison to be complete; the
Alembic environment imports it explicitly for exactly that reason.
"""

from __future__ import annotations

from pgvector.sqlalchemy import Vector
from sqlalchemy import Column, Index, String, Table, UniqueConstraint

from smart_home.infrastructure.database.tables import Base

TABLE_NAME = "reference_phrases"
COLUMN_ID = "id"
COLUMN_INTENT = "intent"
COLUMN_PHRASE = "phrase"
COLUMN_EMBEDDING = "embedding"

EMBEDDING_DIMENSIONS = 384
INTENT_WIDTH = 32
PHRASE_WIDTH = 200
IDENTIFIER_LENGTH = 36

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

NEAREST_LABEL = "distance"
TOP_MATCHES = 3
