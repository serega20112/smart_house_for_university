"""Text encoder port and its implementations."""

from __future__ import annotations

import hashlib
import math
from abc import ABC, abstractmethod


class Embedder(ABC):
    """Turns phrases into normalized vectors."""

    @abstractmethod
    def encode(self, texts: list[str]) -> list[list[float]]:
        """Return the vector representation of each phrase.

        Args:
            texts: Phrases to encode.

        Returns:
            list[list[float]]: One vector per phrase.
        """


class SentenceTransformerEmbedder(Embedder):
    """Encoder backed by a multilingual sentence transformers model."""

    def __init__(self, model_name: str, device: str = "cpu") -> None:
        """Load the model.

        Args:
            model_name: Name of the sentence transformers model.
            device: Torch device used for inference.

        Returns:
            None.
        """
        from sentence_transformers import SentenceTransformer

        self._model = SentenceTransformer(model_name, device=device)

    def encode(self, texts: list[str]) -> list[list[float]]:
        """Return the vector representation of each phrase.

        Args:
            texts: Phrases to encode.

        Returns:
            list[list[float]]: One vector per phrase.
        """
        vectors = self._model.encode(texts, normalize_embeddings=True)
        return [list(map(float, vector)) for vector in vectors]


class LexicalHashEmbedder(Embedder):
    """Dependency free fallback encoder based on hashed tokens."""

    def __init__(self, dimension: int = 512) -> None:
        """Initialize the encoder.

        Args:
            dimension: Size of the produced vectors.

        Returns:
            None.
        """
        self._dimension = dimension

    def encode(self, texts: list[str]) -> list[list[float]]:
        """Return the vector representation of each phrase.

        Args:
            texts: Phrases to encode.

        Returns:
            list[list[float]]: One vector per phrase.
        """
        return [self._encode_one(text) for text in texts]

    def _encode_one(self, text: str) -> list[float]:
        vector = [0.0] * self._dimension
        for token in tokenize(text):
            digest = hashlib.md5(token.encode("utf-8")).hexdigest()
            vector[int(digest, 16) % self._dimension] += 1.0
        norm = math.sqrt(sum(value * value for value in vector)) or 1.0
        return [value / norm for value in vector]


def tokenize(text: str) -> list[str]:
    """Split a phrase into lowercase alphanumeric tokens.

    Args:
        text: Phrase to split.

    Returns:
        list[str]: Tokens of the phrase.
    """
    lowered = text.lower().strip()
    cleaned = "".join(character if character.isalnum() else " " for character in lowered)
    return [token for token in cleaned.split() if token]


def try_build_embedder(model_name: str, device: str) -> Embedder | None:
    """Load the transformer encoder, returning None when it is unavailable.

    Args:
        model_name: Name of the sentence transformers model.
        device: Torch device used for inference.

    Returns:
        Embedder | None: Loaded encoder or None when the model cannot be used.
    """
    try:
        return SentenceTransformerEmbedder(model_name, device=device)
    except Exception:
        return None
