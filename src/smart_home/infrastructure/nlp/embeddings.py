"""Turning phrases into vectors.

The classifier compares meanings, so it needs a real semantic encoder. A hashed
bag of words cannot tell "выключи свет" from "включи свет" apart in any direction
that matters, which is why no fallback encoder exists in this package: a system
that silently degrades to a meaningless similarity is worse than a system that
refuses to start.

The model is loaded from the configuration, and a missing dependency raises
:class:`EmbeddingsUnavailableError` before the first request is served.
"""

from __future__ import annotations

import asyncio
from collections.abc import Sequence
from typing import Protocol

from smart_home.infrastructure.logging import get_logger

log = get_logger("nlp.embeddings")

INSTALL_HINT = (
    "sentence-transformers is required for the local intent classifier; "
    "install the optional extra with 'pip install .[embeddings]'"
)


class EmbeddingsUnavailableError(RuntimeError):
    """The sentence embedding model cannot be loaded.

    Args:
        model_name: Name of the model that was asked for.
        reason: What the loader reported.

    Returns:
        None.
    """

    def __init__(self, model_name: str, reason: str) -> None:
        """Initialize the failure.

        Args:
            model_name: Name of the model that was asked for.
            reason: What the loader reported.

        Returns:
            None.
        """
        super().__init__(f"cannot load the embedding model {model_name!r}: {reason}")
        self.model_name = model_name


class Embedder(Protocol):
    """Produces the normalized vector of a phrase."""

    def encode(self, texts: Sequence[str]) -> list[list[float]]:
        """Return the vector representation of each phrase.

        Args:
            texts: Phrases to encode.

        Returns:
            list[list[float]]: One vector per phrase.
        """


class SentenceTransformerEmbedder(Embedder):
    """Encoder backed by a multilingual sentence transformers model.

    Args:
        model_name: Name of the sentence transformers model.
        device: Torch device used for inference.
        dimensions: Expected length of a produced vector.

    Returns:
        None.

    Raises:
        EmbeddingsUnavailableError: When the library or the model cannot be
            loaded.
    """

    def __init__(self, model_name: str, device: str, dimensions: int) -> None:
        """Load the model.

        Args:
            model_name: Name of the sentence transformers model.
            device: Torch device used for inference.
            dimensions: Expected length of a produced vector.

        Returns:
            None.

        Raises:
            EmbeddingsUnavailableError: When the library or the model cannot be
                loaded.
        """
        try:
            from sentence_transformers import SentenceTransformer
        except ImportError as error:
            raise EmbeddingsUnavailableError(model_name, INSTALL_HINT) from error
        try:
            self._model = SentenceTransformer(model_name, device=device)
        except Exception as error:
            raise EmbeddingsUnavailableError(model_name, str(error)) from error
        self._dimensions = dimensions
        self._name = model_name
        log.info(
            "nlp.embedder_loaded",
            model=model_name,
            device=device,
            dimensions=dimensions,
        )

    def encode(self, texts: Sequence[str]) -> list[list[float]]:
        """Return the vector representation of each phrase.

        Args:
            texts: Phrases to encode.

        Returns:
            list[list[float]]: One normalized vector per phrase.

        Raises:
            EmbeddingsUnavailableError: When the model produced a vector of an
                unexpected length, which would silently corrupt every search.
        """
        if not texts:
            return []
        vectors = self._model.encode(
            list(texts), normalize_embeddings=True, show_progress_bar=False
        )
        encoded = [[float(value) for value in vector] for vector in vectors]
        for vector in encoded:
            if len(vector) != self._dimensions:
                raise EmbeddingsUnavailableError(
                    self._name,
                    f"the model produced {len(vector)} dimensions instead of {self._dimensions}",
                )
        return encoded

    async def encode_async(self, texts: Sequence[str]) -> list[list[float]]:
        """Return the vector representation of each phrase off the event loop.

        Args:
            texts: Phrases to encode.

        Returns:
            list[list[float]]: One normalized vector per phrase.
        """
        return await asyncio.to_thread(self.encode, texts)


def load_embedder(model_name: str, device: str, dimensions: int) -> Embedder:
    """Load the encoder named by the configuration.

    Args:
        model_name: Name of the sentence transformers model.
        device: Torch device used for inference.
        dimensions: Expected length of a produced vector.

    Returns:
        Embedder: Loaded encoder.

    Raises:
        EmbeddingsUnavailableError: When the library or the model cannot be
            loaded.
    """
    return SentenceTransformerEmbedder(model_name, device, dimensions)
