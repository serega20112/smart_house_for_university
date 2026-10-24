"""Понимание фразы: кодировщик, индекс опорных фраз и конвейер понимания."""

from __future__ import annotations

import httpx
from dishka import Provider, Scope, provide
from sqlalchemy.ext.asyncio import AsyncEngine

from backend.application.interfaces.services.language.command_understanding import (
    CommandUnderstandingPort,
)
from backend.application.interfaces.services.language.embedder import Embedder
from backend.application.interfaces.services.language.phrase_index import PhraseIndex
from backend.application.services.language.parser import SentenceParser
from backend.application.services.language.remote_understanding import RemoteFirstUnderstanding
from backend.application.services.language.understanding import (
    ReferencePhraseSeeder,
    VocabularyUnderstanding,
)
from backend.config.settings import Settings
from backend.infrastructure.nlp.embeddings import load_embedder
from backend.infrastructure.nlp.phrases import PgVectorPhraseIndex
from backend.infrastructure.nlp.remote_client import RemoteUnderstandingClient

APP = Scope.APP


class PhrasesProvider(Provider):
    """Конвейер понимания, его драйверы и шаг, наполняющий индекс."""

    @provide(scope=APP)
    def embedder(self, settings: Settings) -> Embedder:
        """Загружает кодировщик, названный настройкой."""
        return load_embedder(
            model_name=settings.language_model_name,
            device=settings.language_device,
            dimensions=settings.language_embedding_dimensions,
        )

    @provide(scope=APP)
    def phrase_index(self, engine: AsyncEngine) -> PhraseIndex:
        """Собирает индекс опорных фраз поверх pgvector."""
        return PgVectorPhraseIndex(engine)

    @provide(scope=APP)
    def sentence_parser(self) -> SentenceParser:
        """Собирает читателя параметров предложения."""
        return SentenceParser()

    @provide(scope=APP)
    def local_understanding(
        self,
        index: PhraseIndex,
        embedder: Embedder,
        parser: SentenceParser,
        settings: Settings,
    ) -> VocabularyUnderstanding:
        """Собирает местный конвейер: словарь опорных фраз и разбор параметров."""
        return VocabularyUnderstanding(
            index=index,
            embedder=embedder,
            parser=parser,
            threshold=settings.language_confidence_threshold,
        )

    @provide(scope=APP)
    def understanding(
        self,
        local: VocabularyUnderstanding,
        client: httpx.AsyncClient,
        settings: Settings,
    ) -> CommandUnderstandingPort:
        """Собирает конвейер, который попросило развёртывание.

        Без удалённой модели остаётся местный конвейер: дом понимает фразы и без неё,
        поэтому клиент строят только когда развёртывание назвал и службу, и режим.
        """
        if not settings.language_neural_commands or not settings.language_bootstrap_url:
            return local
        remote = RemoteUnderstandingClient(
            client=client,
            base_url=settings.language_bootstrap_url,
            timeout_sec=settings.language_timeout_sec,
        )
        return RemoteFirstUnderstanding(remote=remote, local=local)

    @provide(scope=APP)
    def reference_phrase_seeder(
        self, index: PhraseIndex, embedder: Embedder
    ) -> ReferencePhraseSeeder:
        """Собирает стартовый шаг, дописывающий недостающие опорные фразы."""
        return ReferencePhraseSeeder(index=index, embedder=embedder)
