"""Фабрика FastAPI-приложения.

Собирает приложение с одним контейнером Dishka, навешивает API и поднимает в
жизненном цикле транспорт плат, концентратор событий и бота, а на остановке их
же и гасит.

Приложение ровно одно на все аккаунты. Здесь ничего не заводится отдельно для
человека: дом появляется в тот момент, когда человек регистрируется, потому что
именно регистрация создаёт его устройства, настройки и панель.
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from dishka.integrations.fastapi import setup_dishka
from fastapi import FastAPI

from backend import __version__
from backend.application.interface.services.session_token_issuer import SessionTokenIssuer
from backend.application.services.command_dispatcher import CommandDispatcher
from backend.config import Settings
from backend.infrastructure.di import Container, build_dishka_container
from backend.infrastructure.esp.connection import EspConnection
from backend.infrastructure.logging import configure_logging, get_logger
from backend.infrastructure.nlp.classifier import ReferencePhraseSeeder
from backend.infrastructure.nlp.embeddings import EmbeddingsUnavailableError
from backend.infrastructure.redis.chat_sessions import RedisChatSessionStore
from backend.infrastructure.redis.event_broker import RedisSubscriber
from backend.infrastructure.telegram.client import TelegramBotClient
from backend.infrastructure.telegram.linking import TelegramLinkTokenIssuer
from backend.presentation.api import api_router
from backend.presentation.dependencies import bind
from backend.presentation.errors import install_error_handlers
from backend.presentation.messages import CommandReplyComposer, NotificationFactoryImpl
from backend.presentation.telegram.conversation import TelegramConversation
from backend.presentation.telegram.updates import TelegramUpdates
from backend.presentation.web.frontend import mount_frontend
from backend.presentation.websocket.endpoint import router as websocket_router
from backend.presentation.websocket.hub import WebSocketHub

log = get_logger("app")


def create_app(settings: Settings | None = None) -> FastAPI:
    """Собирает FastAPI-приложение.

    Args:
        settings: Конфигурация, из которой строится граф; по умолчанию — та, что
            читает окружение.

    Returns:
        FastAPI: Собранное приложение.
    """
    settings = settings or Settings()
    configure_logging(settings.app_log_level)

    container = build_dishka_container(
        settings,
        notifications=NotificationFactoryImpl(),
    )

    app = FastAPI(
        title=settings.app_name,
        version=__version__,
    )
    app.state.container = container

    setup_dishka(container=container, app=app)

    app.include_router(api_router, prefix="/api")
    app.include_router(websocket_router)
    install_error_handlers(app)
    mount_frontend(app)

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        """Запускает и останавливает все подсистемы приложения.

        Args:
            app: Запускаемое приложение.

        Yields:
            None, пока приложение работает.
        """
        connection = await container.get(EspConnection)
        hub = WebSocketHub(await container.get(RedisSubscriber))
        bind(app, hub=hub, tokens=await container.get(SessionTokenIssuer))
        await connection.start()
        await _seed_reference_phrases(container)
        bot = await _start_telegram(container, settings)
        try:
            yield
        finally:
            if bot is not None:
                await bot.stop()
            await connection.stop()
            await hub.stop()
            await container.close()

    app.router.lifespan_context = lifespan

    return app


async def _seed_reference_phrases(container: Container) -> None:
    """Дописывает в индекс недостающие опорные фразы.

    Дом работает и без понимания фраз: реле, автоматика и сценарии ничего у
    модели не просят, поэтому отсутствующий кодировщик записывается в журнал и не
    мешает запуску. Сам посев при этом происходит явно на старте: индекс, который
    наполняется первым же вопросом, превращает первый запрос в ожидание.

    Args:
        container: Граф зависимостей запущенного процесса.
    """
    try:
        seeder = await container.get(ReferencePhraseSeeder)
        await seeder.seed()
    except EmbeddingsUnavailableError as error:
        log.warning("nlp.embeddings_unavailable", error=str(error))


async def _start_telegram(container: Container, settings: Settings) -> TelegramBotClient | None:
    """Поднимает опрос бота, если развёртывание его включило.

    Бот — второй способ сказать то же самое, что и в интерфейсе, поэтому ему
    отдают ровно ту же шину команд и те же фразы. Недоступный мессендер не
    имеет права выключать дом: сбой записывается в журнал, а приложение
    продолжает работать без бота.

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
