"""Natural language pipeline settings."""

from __future__ import annotations

import os


def model_name() -> str:
    """Return the sentence-transformers model used for embeddings.

    Returns:
        str: Model name.
    """
    return os.getenv("NLP_MODEL_NAME", "paraphrase-multilingual-MiniLM-L12-v2")


def device() -> str:
    """Return the torch device used to run the embedding model.

    Returns:
        str: Device name.
    """
    return os.getenv("NLP_DEVICE", "cpu")


def confidence_threshold() -> float:
    """Return the similarity below which a command requires clarification.

    Returns:
        float: Threshold between 0 and 1.
    """
    return float(os.getenv("NLP_CONFIDENCE_THRESHOLD", "0.55"))


def allow_lexical_fallback() -> bool:
    """Return whether the lexical embedder may replace the missing model.

    Returns:
        bool: True when the fallback is allowed.
    """
    return os.getenv("NLP_ALLOW_LEXICAL_FALLBACK", "1") == "1"
