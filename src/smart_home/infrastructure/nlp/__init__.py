"""Natural language understanding.

``vocabulary``
    every Russian word the pipeline knows, and the reference phrases of every
    intent.
``parser``
    the typed values a sentence carries.
``embeddings``
    the sentence encoder.
``classifier``
    the nearest neighbour search over the reference phrases in Postgres.
``remote``
    the composite that asks a remote model first.
``tables``
    the reference phrase table of the store.
"""

from smart_home.infrastructure.nlp.classifier import (
    IntentMatch,
    ReferencePhraseSeeder,
    VectorIntentClassifier,
)
from smart_home.infrastructure.nlp.embeddings import (
    Embedder,
    EmbeddingsUnavailableError,
    load_embedder,
)
from smart_home.infrastructure.nlp.parser import SentenceFacts, SentenceParser, normalize
from smart_home.infrastructure.nlp.remote import (
    RemoteAnswer,
    RemoteFirstUnderstanding,
    RemoteUnderstandingClient,
    RemoteUnderstandingUnavailable,
)

__all__ = [
    "Embedder",
    "EmbeddingsUnavailableError",
    "IntentMatch",
    "ReferencePhraseSeeder",
    "RemoteAnswer",
    "RemoteFirstUnderstanding",
    "RemoteUnderstandingClient",
    "RemoteUnderstandingUnavailable",
    "SentenceFacts",
    "SentenceParser",
    "VectorIntentClassifier",
    "load_embedder",
    "normalize",
]
