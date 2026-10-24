"""Собирает конвейер понимания из конфигурации.

Композиционный корень зовёт одну функцию и получает готовый конвейер. Какой он будет,
зависит всего от двух настроек: задана ли удалённая модель и насколько уверенным должен
быть местный классификатор.
"""

from __future__ import annotations

import httpx
from sqlalchemy.ext.asyncio import AsyncEngine

from backend.application.interface.services.command_understanding_port import (
    CommandUnderstandingPort,
)
from backend.config.settings import Settings
from backend.infrastructure.nlp.classifier import (
    ReferencePhraseSeeder,
    VectorIntentClassifier,
)
from backend.infrastructure.nlp.embeddings import Embedder, load_embedder
from backend.infrastructure.nlp.parser import SentenceParser
from backend.infrastructure.nlp.remote import (
    RemoteFirstUnderstanding,
    RemoteUnderstandingClient,
)


def build_local_understanding(
    engine: AsyncEngine, embedder: Embedder, settings: Settings
) -> VectorIntentClassifier:
    """Строит классификатор, работающий по индексу pgvector.

    Args:
        engine: Движок, из которого читают опорные фразы.
        embedder: Кодировщик, превращающий фразу в вектор.
        settings: Конфигурация языкового конвейера.

    Returns:
        VectorIntentClassifier: Местный конвейер.
    """
    return VectorIntentClassifier(
        engine=engine,
        embedder=embedder,
        parser=SentenceParser(),
        confidence_threshold=settings.language_confidence_threshold,
    )


def build_understanding(
    engine: AsyncEngine,
    embedder: Embedder,
    client: httpx.AsyncClient,
    settings: Settings,
) -> CommandUnderstandingPort:
    """Строит конвейер понимания, какой попросило развёртывание.

    Args:
        engine: Движок, из которого читают опорные фразы.
        embedder: Кодировщик, превращающий фразу в вектор.
        client: Соединение с хостом удалённой модели.
        settings: Конфигурация языкового конвейера.

    Returns:
        CommandUnderstandingPort: Местный конвейер, а при настроенной удалённой модели —
        составной, где первым идёт удалённая.
    """
    local = build_local_understanding(engine, embedder, settings)
    if not settings.language_neural_commands or not settings.language_bootstrap_url:
        return local
    remote = RemoteUnderstandingClient(
        client=client,
        base_url=settings.language_bootstrap_url,
        timeout_sec=settings.language_timeout_sec,
    )
    return RemoteFirstUnderstanding(remote=remote, local=local)


def build_embedder(settings: Settings) -> Embedder:
    """Загружает кодировщик, названный в конфигурации.

    Args:
        settings: Конфигурация языкового конвейера.

    Returns:
        Embedder: Загруженный кодировщик.

    Raises:
        EmbeddingsUnavailableError: Когда библиотеку или модель не удалось загрузить.
    """
    return load_embedder(
        model_name=settings.language_model_name,
        device=settings.language_device,
        dimensions=settings.language_embedding_dimensions,
    )


def build_reference_phrase_seeder(engine: AsyncEngine, embedder: Embedder) -> ReferencePhraseSeeder:
    """Строит шаг запуска, наполняющий индекс опорных фраз.

    Args:
        engine: Движок, в который записывают опорные фразы.
        embedder: Кодировщик, превращающий фразу в вектор.

    Returns:
        ReferencePhraseSeeder: Заполнитель индекса.
    """
    return ReferencePhraseSeeder(engine=engine, embedder=embedder)
