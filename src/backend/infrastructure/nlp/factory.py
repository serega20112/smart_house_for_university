"""Building the understanding pipeline from the configuration.

The composition root calls one function and receives a ready pipeline. Which
pipeline that is depends on two settings only: whether a remote model is
configured, and how sure the local classifier has to be.
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
    """Build the classifier running against the pgvector index.

    Args:
        engine: Engine the reference phrases are read from.
        embedder: Encoder turning a phrase into a vector.
        settings: Configuration of the language pipeline.

    Returns:
        VectorIntentClassifier: Local pipeline.
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
    """Build the understanding pipeline the deployment asked for.

    Args:
        engine: Engine the reference phrases are read from.
        embedder: Encoder turning a phrase into a vector.
        client: Connection to the remote model host.
        settings: Configuration of the language pipeline.

    Returns:
        CommandUnderstandingPort: Local pipeline, or the remote first composite
        when a remote model is configured.
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
    """Load the encoder named by the configuration.

    Args:
        settings: Configuration of the language pipeline.

    Returns:
        Embedder: Loaded encoder.

    Raises:
        EmbeddingsUnavailableError: When the library or the model cannot be
            loaded.
    """
    return load_embedder(
        model_name=settings.language_model_name,
        device=settings.language_device,
        dimensions=settings.language_embedding_dimensions,
    )


def build_reference_phrase_seeder(engine: AsyncEngine, embedder: Embedder) -> ReferencePhraseSeeder:
    """Build the startup step filling the reference phrase index.

    Args:
        engine: Engine the reference phrases are written to.
        embedder: Encoder turning a phrase into a vector.

    Returns:
        ReferencePhraseSeeder: Seeder of the index.
    """
    return ReferencePhraseSeeder(engine=engine, embedder=embedder)
