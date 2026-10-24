"""Понимание обычного текста.

``vocabulary``
    всякое русское слово, которое знает конвейер, и опорные фразы каждого намерения.
``parser``
    типизированные значения, которые несёт предложение.
``embeddings``
    кодировщик предложений.
``classifier``
    поиск ближайшего соседа по опорным фразам в Postgres.
``remote``
    составной конвейер, сперва спрашивающий удалённую модель.
"""

from backend.infrastructure.nlp.classifier import (
    IntentMatch,
    ReferencePhraseSeeder,
    VectorIntentClassifier,
)
from backend.infrastructure.nlp.embeddings import (
    Embedder,
    EmbeddingsUnavailableError,
    load_embedder,
)
from backend.infrastructure.nlp.parser import SentenceFacts, SentenceParser, normalize
from backend.infrastructure.nlp.remote import (
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
