"""Драйверы понимания фраз: то, что говорит с внешним миром.

В этом пакете нет ни словаря, ни разбора предложения, ни решений о том, достаточна ли
уверенность, — всё это в `application/services/language`. Здесь только кодировщик
torch, индекс опорных фраз в pgvector и HTTP-клиент службы моделей.

``embeddings``
    кодировщик предложений на модели sentence transformers.
``phrases``
    поиск ближайшего соседа и запись опорных фраз в Postgres.
``remote_client``
    запрос к машине, крутящей модели, и разбор ответа её протокола.
"""

from backend.infrastructure.nlp.embeddings import (
    SentenceTransformerEmbedder,
    load_embedder,
)
from backend.infrastructure.nlp.phrases import PgVectorPhraseIndex
from backend.infrastructure.nlp.remote_client import RemoteUnderstandingClient

__all__ = [
    "PgVectorPhraseIndex",
    "RemoteUnderstandingClient",
    "SentenceTransformerEmbedder",
    "load_embedder",
]
