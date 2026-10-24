"""Понимание фразы: словарь, кодировщик, индекс опорных фраз и конвейер понимания.

Модель — необязательная часть развёртывания. Словарь узнаёт знакомые фразы сам, поэтому
отсутствующая зависимость кодировщика не валит процесс и не оставляет дом без команд:
она только снимает смысловой разбор, а непонятое предложение честно отвечает, что модели
нет, вместо внутренней ошибки.
"""

from __future__ import annotations

import httpx
from dishka import Provider, Scope, provide
from sqlalchemy.ext.asyncio import AsyncEngine

from backend.application.errors import LanguageModelUnavailable
from backend.application.interfaces.services.language.command_understanding import (
    CommandUnderstandingPort,
)
from backend.application.interfaces.services.language.embedder import Embedder
from backend.application.interfaces.services.language.phrase_index import PhraseIndex
from backend.application.services.language.lexicon_understanding import (
    DictionaryFirstUnderstanding,
    LexiconUnderstanding,
)
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
from backend.infrastructure.system.logging import get_logger

APP = Scope.APP

log = get_logger("nlp.phrases")


class PhrasesProvider(Provider):
    """Конвейер понимания, его драйверы и шаг, наполняющий индекс."""

    @provide(scope=APP)
    def embedder(self, settings: Settings) -> Embedder | None:
        """Загружает кодировщик, названный настройкой, если он вообще есть.

        Returns:
            Embedder | None: Загруженный кодировщик либо None, когда необязательная
            зависимость модели не установлена или модель не открылась.
        """
        try:
            return load_embedder(
                model_name=settings.language_model_name,
                device=settings.language_device,
                dimensions=settings.language_embedding_dimensions,
            )
        except LanguageModelUnavailable as error:
            log.warning("nlp.embeddings_unavailable", error=str(error))
            return None

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
        embedder: Embedder | None,
        parser: SentenceParser,
        settings: Settings,
    ) -> VocabularyUnderstanding | None:
        """Собирает смысловой конвейер, если этому развёртыванию есть чем кодировать.

        Args:
            index: Индекс опорных фраз.
            embedder: Кодировщик этого развёртывания или None, когда его нет.
            parser: Читатель параметров предложения.
            settings: Конфигурация с порогом уверенности.

        Returns:
            VocabularyUnderstanding | None: Конвейер ближайшей опорной фразы либо None,
            когда кодировщика нет.
        """
        if embedder is None:
            return None
        return VocabularyUnderstanding(
            index=index,
            embedder=embedder,
            parser=parser,
            threshold=settings.language_confidence_threshold,
        )

    @provide(scope=APP)
    def understanding(
        self,
        parser: SentenceParser,
        local: VocabularyUnderstanding | None,
        client: httpx.AsyncClient,
        settings: Settings,
    ) -> CommandUnderstandingPort:
        """Собирает конвейер, который попросило развёртывание.

        Словарь идёт первым всегда: знакомые фразы он узнаёт без кодирования, а это
        самая частая часть потока. Смысловой конвейер спрашивают только о непонятом,
        и только если в развёртывании он есть.

        Args:
            parser: Читатель параметров предложения.
            local: Местный смысловой конвейер или None, когда кодировщика нет.
            client: HTTP-клиент для службы моделей.
            settings: Конфигурация, включающая удалённую модель.

        Returns:
            CommandUnderstandingPort: Собранный конвейер понимания.
        """
        dictionary = LexiconUnderstanding(parser=parser)
        semantic: CommandUnderstandingPort | None = local
        if (
            semantic is not None
            and settings.language_neural_commands
            and settings.language_bootstrap_url
        ):
            remote = RemoteUnderstandingClient(
                client=client,
                base_url=settings.language_bootstrap_url,
                timeout_sec=settings.language_timeout_sec,
            )
            semantic = RemoteFirstUnderstanding(remote=remote, local=semantic)
        if semantic is None:
            return dictionary
        return DictionaryFirstUnderstanding(dictionary=dictionary, semantic=semantic)

    @provide(scope=APP)
    def reference_phrase_seeder(
        self, index: PhraseIndex, embedder: Embedder | None
    ) -> ReferencePhraseSeeder:
        """Собирает стартовый шаг, дописывающий недостающие опорные фразы."""
        return ReferencePhraseSeeder(index=index, embedder=embedder)
