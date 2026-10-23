"""Intent classification over a pgvector index of reference phrases.

A sentence is embedded once and matched against the reference phrases of every
intent with the cosine distance operator of Postgres, so the nearest neighbours
come back from the store itself instead of from a list this process happens to
hold. The index behind the column is an HNSW graph, which is what keeps the
search fast enough to run on every sentence the interface receives.

The parameters of a sentence are not guessed here: the classifier produces the
intent and the confidence, and the parser produces the typed values the
application asked for.
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.engine import RowMapping
from sqlalchemy.ext.asyncio import AsyncConnection, AsyncEngine

from backend.application.dto.language.command_understanding import CommandUnderstanding
from backend.application.dto.language.intent import Intent
from backend.application.interface.services.command_understanding_port import (
    CommandUnderstandingPort,
)
from backend.infrastructure.database.tables.reference_phrases import (
    COLUMN_EMBEDDING,
    COLUMN_ID,
    COLUMN_INTENT,
    COLUMN_PHRASE,
    NEAREST_LABEL,
    REFERENCE_PHRASES,
)
from backend.infrastructure.logging import get_logger
from backend.infrastructure.nlp import vocabulary
from backend.infrastructure.nlp.embeddings import Embedder
from backend.infrastructure.nlp.parser import SentenceParser

log = get_logger("nlp.classifier")


@dataclass(frozen=True, slots=True)
class IntentMatch:
    """The nearest reference phrase of a sentence.

    Args:
        intent: Intent the phrase stands for.
        phrase: Reference phrase that was matched.
        confidence: Cosine similarity between zero and one.

    Returns:
        None.
    """

    intent: Intent
    phrase: str
    confidence: float


class VectorIntentClassifier(CommandUnderstandingPort):
    """Understands a sentence with a pgvector nearest neighbour search.

    Args:
        engine: Engine the reference phrases are read from.
        embedder: Encoder turning a sentence into a vector.
        parser: Reader of the parameters of a sentence.
        confidence_threshold: Score a home changing intent has to reach.

    Returns:
        None.
    """

    def __init__(
        self,
        engine: AsyncEngine,
        embedder: Embedder,
        parser: SentenceParser,
        confidence_threshold: float,
    ) -> None:
        """Initialize the classifier.

        Args:
            engine: Engine the reference phrases are read from.
            embedder: Encoder turning a sentence into a vector.
            parser: Reader of the parameters of a sentence.
            confidence_threshold: Score a home changing intent has to reach.

        Returns:
            None.
        """
        self._engine = engine
        self._embedder = embedder
        self._parser = parser
        self._threshold = confidence_threshold

    async def understand(self, text: str) -> CommandUnderstanding:
        """Interpret a sentence.

        Args:
            text: Raw sentence as the interface received it.

        Returns:
            CommandUnderstanding: What the pipeline made of it. The intent is
            None when the index holds nothing comparable to the sentence.
        """
        facts = self._parser.parse(text)
        match = await self.classify(text)
        return CommandUnderstanding(
            intent=None if match is None else match.intent,
            device_name=facts.device_name,
            device_kinds=facts.device_kinds,
            capability=facts.capability,
            temperature=facts.temperature,
            humidity=facts.humidity,
            delay_minutes=facts.delay_minutes,
            target=facts.target,
            confidence=0.0 if match is None else match.confidence,
        )

    async def is_confident_enough(self, understanding: CommandUnderstanding) -> bool:
        """Return whether an understanding may be carried out.

        The threshold guards the intents that change the home. Asking how warm it
        is cannot break anything, so a weak match of a read only intent is still
        answered instead of turning into a question.

        Args:
            understanding: Result of the pipeline.

        Returns:
            bool: True when the command may proceed.
        """
        intent = understanding.intent
        if intent is None or not intent.changes_the_home:
            return True
        return understanding.confidence >= self._threshold

    async def classify(self, text: str) -> IntentMatch | None:
        """Return the nearest reference phrase of a sentence.

        Args:
            text: Raw sentence as the interface received it.

        Returns:
            IntentMatch | None: Nearest reference phrase, or None when the index
            is empty or holds nothing comparable.
        """
        vectors = await asyncio.to_thread(self._embedder.encode, [text])
        if not vectors:
            return None
        async with self._engine.connect() as connection:
            rows = await _nearest(connection, vectors[0])
        if not rows:
            return None
        intent = Intent.parse(rows[0][COLUMN_INTENT])
        if intent is None:
            return None
        return IntentMatch(
            intent=intent,
            phrase=str(rows[0][COLUMN_PHRASE]),
            confidence=round(1.0 - float(rows[0][NEAREST_LABEL]), 4),
        )


async def _nearest(connection: AsyncConnection, vector: list[float]) -> list[RowMapping]:
    """Возвращает ближайшую опорную фразу вместе с расстоянием до неё."""
    statement = (
        select(
            REFERENCE_PHRASES.c[COLUMN_INTENT],
            REFERENCE_PHRASES.c[COLUMN_PHRASE],
            REFERENCE_PHRASES.c[COLUMN_EMBEDDING].cosine_distance(vector).label(NEAREST_LABEL),
        )
        .where(REFERENCE_PHRASES.c[COLUMN_EMBEDDING].is_not(None))
        .order_by(NEAREST_LABEL)
        .limit(1)
    )
    result = await connection.execute(statement)
    return list(result.mappings())


class ReferencePhraseSeeder:
    """Fills the index with the reference phrases of the vocabulary.

    Seeding is an explicit startup step rather than a side effect of a search:
    an index that fills itself the first time somebody asks a question turns a
    slow first request into a timeout.

    Args:
        engine: Engine the reference phrases are written to.
        embedder: Encoder turning a phrase into a vector.

    Returns:
        None.
    """

    def __init__(self, engine: AsyncEngine, embedder: Embedder) -> None:
        """Initialize the seeder.

        Args:
            engine: Engine the reference phrases are written to.
            embedder: Encoder turning a phrase into a vector.

        Returns:
            None.
        """
        self._engine = engine
        self._embedder = embedder

    async def seed(self) -> int:
        """Store every reference phrase of the vocabulary that is missing.

        Returns:
            int: Number of rows that were written.
        """
        pairs = vocabulary.reference_pairs()
        async with self._engine.begin() as connection:
            stored = await _stored_phrases(connection)
            missing = [pair for pair in pairs if pair not in stored]
            if not missing:
                return 0
            vectors = await asyncio.to_thread(
                self._embedder.encode, [phrase for _intent, phrase in missing]
            )
            await connection.execute(
                insert(REFERENCE_PHRASES).values(
                    [
                        {
                            COLUMN_ID: str(uuid4()),
                            COLUMN_INTENT: intent,
                            COLUMN_PHRASE: phrase,
                            COLUMN_EMBEDDING: vector,
                        }
                        for (intent, phrase), vector in zip(missing, vectors, strict=True)
                    ]
                )
            )
        log.info("nlp.reference_phrases_seeded", written=len(missing))
        return len(missing)


async def _stored_phrases(connection: AsyncConnection) -> set[tuple[str, str]]:
    """Возвращает пары «намерение — фраза», которые уже лежат в индексе."""
    result = await connection.execute(
        select(REFERENCE_PHRASES.c[COLUMN_INTENT], REFERENCE_PHRASES.c[COLUMN_PHRASE])
    )
    return {(str(row[COLUMN_INTENT]), str(row[COLUMN_PHRASE])) for row in result.mappings().all()}
