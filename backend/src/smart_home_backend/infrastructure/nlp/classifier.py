"""Intent classifier built on embeddings and vector search."""

from __future__ import annotations

import asyncio

from smart_home_backend.application.interface.services import IntentClassifier, IntentPrediction
from smart_home_backend.infrastructure.nlp.embedder import Embedder
from smart_home_backend.infrastructure.nlp.references import reference_pairs
from smart_home_backend.infrastructure.nlp.vector_index import VectorIndex

UNKNOWN_INTENT = "UNKNOWN"


class EmbeddingIntentClassifier(IntentClassifier):
    """Matches a command against the reference phrases of every intent."""

    def __init__(
        self,
        embedder: Embedder,
        references: list[tuple[str, str]] | None = None,
    ) -> None:
        """Index the reference phrases.

        Args:
            embedder: Encoder producing the vectors.
            references: Intent and phrase pairs, defaults to the built-in ones.

        Returns:
            None.
        """
        self._embedder = embedder
        self._index = VectorIndex()
        pairs = references if references is not None else reference_pairs()
        phrases = [phrase for _intent, phrase in pairs]
        vectors = embedder.encode(phrases)
        for (intent, phrase), vector in zip(pairs, vectors, strict=True):
            self._index.add(intent, phrase, vector)

    async def classify(self, text: str) -> IntentPrediction:
        """Predict the intent of a command.

        Encoding may block, so it runs in a worker thread to keep the event loop
        responsive.

        Args:
            text: Raw command text.

        Returns:
            IntentPrediction: Predicted intent and confidence.
        """
        vector = (await asyncio.to_thread(self._embedder.encode, [text]))[0]
        match = self._index.search(vector)
        if match is None:
            return IntentPrediction(intent=UNKNOWN_INTENT, confidence=0.0)
        return IntentPrediction(
            intent=match.intent,
            confidence=round(min(1.0, max(0.0, match.score)), 4),
            matched_example=match.phrase,
        )
