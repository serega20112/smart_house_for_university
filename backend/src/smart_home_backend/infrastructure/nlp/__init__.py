"""Natural language pipeline infrastructure.

Builds the classifier and the parser, preferring a real embedding model and
falling back to a lexical one when the model cannot be loaded.
"""

from __future__ import annotations

from smart_home_backend.application.interface.services import CommandParser, IntentClassifier
from smart_home_backend.config import Settings
from smart_home_backend.infrastructure.logging_config import get_logger
from smart_home_backend.infrastructure.nlp.classifier import EmbeddingIntentClassifier
from smart_home_backend.infrastructure.nlp.embedder import (
    Embedder,
    LexicalHashEmbedder,
    try_build_embedder,
)
from smart_home_backend.infrastructure.nlp.parser import RuleCommandParser
from smart_home_backend.infrastructure.nlp.references import INTENT_REFERENCES, reference_pairs
from smart_home_backend.infrastructure.nlp.vector_index import Match, VectorIndex, cosine

log = get_logger("nlp")


def build_embedder(settings: Settings) -> Embedder:
    """Return the encoder to classify commands with.

    Args:
        settings: Application settings.

    Returns:
        Embedder: Transformer encoder or the lexical fallback.
    """
    embedder = try_build_embedder(settings.nlp_model_name, settings.nlp_device)
    if embedder is not None:
        log.info(
            "Embeddings model loaded",
            extra={"ctx": {"model": settings.nlp_model_name}},
        )
        return embedder
    if not settings.nlp_allow_lexical_fallback:
        raise RuntimeError(
            "The embeddings model is unavailable and the lexical fallback is disabled"
        )
    log.info("Embeddings model unavailable, using the lexical encoder")
    return LexicalHashEmbedder()


def build_intent_classifier(settings: Settings) -> IntentClassifier:
    """Build the intent classifier.

    Args:
        settings: Application settings.

    Returns:
        IntentClassifier: Classifier ready to use.
    """
    return EmbeddingIntentClassifier(build_embedder(settings))


def build_command_parser() -> CommandParser:
    """Build the parameter parser.

    Returns:
        CommandParser: Parser ready to use.
    """
    return RuleCommandParser()
