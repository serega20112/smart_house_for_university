"""Жизненный цикл процесса: старт подсистем и их остановка.

Долгоживущие адаптеры (соединение с платами, концентратор событий) описаны провайдерами
области приложения и умеют запускаться и гаситься сами, поэтому отсюда их только
просят. Что осталось на этом месте — то, чего контейнер собрать не может без знаний из
презентационного слоя: разговор бота и посев индекса опорных фраз.
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from dishka import AsyncContainer
from fastapi import FastAPI

from backend.application.services.command_dispatcher import CommandDispatcher
from backend.application.services.language.understanding import ReferencePhraseSeeder
from backend.config.settings import Settings
from backend.infrastructure.brokers.chat_sessions import RedisChatSessionStore
from backend.infrastructure.esp.connection import EspConnection
from backend.infrastructure.nlp.embeddings import EmbeddingsUnavailableError
from backend.infrastructure.security.link_tokens import TelegramLinkTokenIssuer
from backend.infrastructure.system.logging import get_logger
from backend.infrastructure.telegram.client import TelegramBotClient
from backend.infrastructure.websockets.hub import WebSocketHub
from backend.presentation.messages import CommandReplyComposer
from backend.presentation.telegram.conversation import TelegramConversation
from backend.presentation.telegram.updates import TelegramUpdates

log = get_logger("lifecycle")


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Поднимает подсистемы процесса и отпускает их при остановке.

    Args:
        app: Запускаемое приложение.

    Yields:
        None, пока приложение работает.
    """
    container: AsyncContainer = app.state.container
    settings: Settings = await container.get(Settings)
    await container.get(EspConnection)
    await container.get(WebSocketHub)
    await _seed_reference_phrases(container)
    bot = await _start_telegram(container, settings)
    try:
        yield
    finally:
        if bot is not None:
            await bot.stop()
        await container.close()


async def _seed_reference_phrases(container: AsyncContainer) -> None:
    """Дописывает в индекс недостающие опорные фразы.

    Дом работает и без понимания фраз: реле, автоматика и сценарии ничего у модели не
    просят, поэтому отсутствующий кодировщик записывается в журнал и не мешает запуску.
    Сам посев происходит явно на старте: индекс, который наполняется первым же вопросом,
    превращает первый запрос в ожидание.

    Args:
        container: Граф зависимостей запущенного процесса.
    """
    try:
        seeder = await container.get(ReferencePhraseSeeder)
        await seeder.seed()
    except EmbeddingsUnavailableError as error:
        log.warning("nlp.embeddings_unavailable", error=str(error))


async def _start_telegram(
    container: AsyncContainer, settings: Settings
) -> TelegramBotClient | None:
    """Поднимает опрос бота, если развёртывание его включило.

    Бот — второй способ сказать то же самое, что и в интерфейсе, поэтому ему отдают
    ровно ту же шину команд и те же фразы. Недоступный мессендер не имеет права
    выключать дом: сбой записывается в журнал, а приложение продолжает работать без бота.

    Args:
        container: Граф зависимостей запущенного процесса.
        settings: Конфигурация, которой развёртывание включает бота.

    Returns:
        TelegramBotClient | None: Запущенный бот либо None, когда его не запустили.
    """
    if not settings.telegram_enabled:
        return None
    bot = await container.get(TelegramBotClient)
    if not bot.enabled:
        log.warning("telegram.disabled_no_token")
        return None
    conversation = TelegramConversation(
        sessions=await container.get(RedisChatSessionStore),
        links=await container.get(TelegramLinkTokenIssuer),
        dispatcher=await container.get(CommandDispatcher),
        composer=CommandReplyComposer(),
    )
    try:
        await bot.start(TelegramUpdates(conversation).handle)
    except Exception as error:
        log.warning("telegram.start_failed", error=str(error))
        return None
    return bot
