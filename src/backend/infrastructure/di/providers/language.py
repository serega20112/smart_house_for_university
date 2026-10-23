"""Понимание фразы: кодировщик предложений, конвейер намерений и посев индекса."""

from __future__ import annotations

import httpx
from dishka import Provider, Scope, provide

from backend.application.interface.services.command_understanding_port import (
    CommandUnderstandingPort,
)
from backend.config.settings import Settings
from backend.infrastructure.database.engine import AsyncEngine
from backend.infrastructure.nlp.classifier import ReferencePhraseSeeder
from backend.infrastructure.nlp.embeddings import Embedder
from backend.infrastructure.nlp.factory import (
    build_embedder,
    build_reference_phrase_seeder,
    build_understanding,
)

APP = Scope.APP


class LanguageProvider(Provider):
    """Конвейер понимания, его кодировщик и шаг, наполняющий индекс."""

    @provide(scope=APP)
    def embedder(self, settings: Settings) -> Embedder:
        """Загружает кодировщик, названный настройкой."""
        return build_embedder(settings)

    @provide(scope=APP)
    def understanding(
        self,
        engine: AsyncEngine,
        embedder: Embedder,
        client: httpx.AsyncClient,
        settings: Settings,
    ) -> CommandUnderstandingPort:
        """Собирает конвейер, который попросило развёртывание."""
        return build_understanding(engine, embedder, client, settings)

    @provide(scope=APP)
    def reference_phrase_seeder(
        self, engine: AsyncEngine, embedder: Embedder
    ) -> ReferencePhraseSeeder:
        """Собирает стартовый шаг, дописывающий недостающие опорные фразы."""
        return build_reference_phrase_seeder(engine, embedder)
