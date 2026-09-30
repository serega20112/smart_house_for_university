"""Vector index over the reference phrases."""

from __future__ import annotations

import math
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class Match:
    """Closest reference found for a query vector.

    Args:
        intent: Intent of the matched reference.
        score: Cosine similarity of the match.
        phrase: Matched reference phrase.

    Returns:
        None.
    """

    intent: str
    score: float
    phrase: str


def cosine(left: list[float], right: list[float]) -> float:
    """Return the cosine similarity of two vectors.

    Args:
        left: First vector.
        right: Second vector.

    Returns:
        float: Similarity between minus one and one.
    """
    dot = sum(a * b for a, b in zip(left, right, strict=False))
    left_norm = math.sqrt(sum(a * a for a in left)) or 1.0
    right_norm = math.sqrt(sum(b * b for b in right)) or 1.0
    return dot / (left_norm * right_norm)


class VectorIndex:
    """In memory index of reference vectors with nearest neighbour search."""

    def __init__(self) -> None:
        """Initialize an empty index.

        Returns:
            None.
        """
        self._vectors: list[list[float]] = []
        self._intents: list[str] = []
        self._phrases: list[str] = []

    def add(self, intent: str, phrase: str, vector: list[float]) -> None:
        """Add a reference to the index.

        Args:
            intent: Intent of the reference.
            phrase: Reference phrase.
            vector: Vector of the reference phrase.

        Returns:
            None.
        """
        self._vectors.append(vector)
        self._intents.append(intent)
        self._phrases.append(phrase)

    def search(self, query: list[float]) -> Match | None:
        """Return the closest reference to a query vector.

        Args:
            query: Query vector.

        Returns:
            Match | None: Closest reference or None when the index is empty.
        """
        if not self._vectors:
            return None
        scores = [cosine(query, vector) for vector in self._vectors]
        best = max(range(len(scores)), key=scores.__getitem__)
        return Match(intent=self._intents[best], score=scores[best], phrase=self._phrases[best])
