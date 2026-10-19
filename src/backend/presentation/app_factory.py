"""FastAPI application factory.

Creates the schema, starts the board connections, the background loops and the
Telegram bot, and shuts everything down cleanly.

There is exactly one application serving every account. Nothing here is seeded
per user: a new home appears the moment a user registers, because registration
is what creates its devices, preferences and dashboard.
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.config import Settings
from backend.config import settings as default_settings
from backend.config.settings import PROJECT_ROOT
from backend.infrastructure.database import create_schema
from backend.infrastructure.di import Container, build_container
from backend.infrastructure.logging_config import configure_logging, get_logger
from backend.infrastructure.telegram import TelegramBotRunner
from backend.infrastructure.voice import VoiceServiceProcess, ensure_voice_service
from backend.presentation.api import api_router
from backend.presentation.telegram import TelegramCommandsHandler
from backend.presentation.voice_composer import CommandReplyComposer
from backend.presentation.web import mount_frontend
from backend.presentation.websocket import WebSocketHub
from backend.presentation.websocket.endpoint import router as websocket_router

log = get_logger("app")


class VoiceState:
    """Voice service of this process, kept so that shutdown can close it.

    Args:
        service: Process started by this backend, or None when the service was
            already running or is not there at all.
        models: What the service reported about itself.

    Returns:
        None.
    """

    def __init__(
        self, service: VoiceServiceProcess | None = None, models: dict | None = None
    ) -> None:
        """Initialize the state.

        Args:
            service: Process started by this backend.
            models: Answer of the service health endpoint.

        Returns:
            None.
        """
        self.service = service
        self.models = models


def create_app(settings: Settings | None = None) -> FastAPI:
    """Build the FastAPI application.

    Args:
        settings: Configuration to build the graph from, defaults to the
            environment configuration.

    Returns:
        FastAPI: Configured application.
    """
    settings = settings or default_settings
    configure_logging(settings.log_level)

    hub = WebSocketHub()
    container = build_container(settings, hub, CommandReplyComposer())
    bot_runner = _build_bot_runner(settings, container)
    voice_state: VoiceState = VoiceState()

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        """Start and stop every subsystem of the application.

        Args:
            app: Application being started.

        Returns:
            AsyncIterator[None]: Lifespan iterator.
        """
        await create_schema(container.engine)
        await container.esp_connection.start()
        await container.scheduler.start()
        await _start_voice(container, voice_state)
        if bot_runner is not None:
            try:
                await bot_runner.start()
            except Exception as exc:
                log.warning("Telegram bot failed to start", extra={"ctx": {"error": str(exc)}})
        log.info("Smart Home backend started")
        try:
            yield
        finally:
            if bot_runner is not None:
                await bot_runner.stop()
            await _stop_voice(container, voice_state)
            await container.scheduler.stop()
            await container.esp_connection.stop()
            await container.engine.dispose()
            log.info("Smart Home backend stopped")

    app = FastAPI(title="Smart Home Backend", version="2.0.0", lifespan=lifespan)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_allowed_origins or ["*"],
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.state.container = container
    app.state.hub = hub
    app.include_router(api_router, prefix="/api")
    app.include_router(websocket_router)

    if not mount_frontend(app):

        @app.get("/", include_in_schema=False)
        async def root() -> dict[str, str]:
            """Return a short description of the service.

            The interface is not built yet, so only the API description is
            served from the root.

            Returns:
                dict[str, str]: Service description.
            """
            return {
                "name": settings.app_name,
                "status": "ok",
                "docs": "/docs",
                "hint": "run npm run build in frontend to serve the interface",
            }

    return app


async def _start_voice(container: Container, state: VoiceState) -> None:
    """Bring the voice pipeline up and report what it found.

    A voice service that is not running is started by this process, because a home
    that only works after a person remembers to start a third program is a home
    that looks broken. A service that is already running is left alone, which keeps
    an installation with the models on another machine working as before.

    Args:
        container: Assembled dependency graph.
        state: Where the started service is remembered for shutdown.

    Returns:
        None.
    """
    settings = container.settings
    if settings.voice_microphone_enabled:
        log.info(
            "microphone of a paired board is opened automatically",
            extra={
                "ctx": {
                    "sample_rate": settings.voice_sample_rate,
                    "continuous": settings.voice_continuous,
                }
            },
        )
    if not settings.voice_active:
        log.info(
            "voice recognition is switched off (VOICE_ENABLED=1 in .env turns it on)",
            extra={"ctx": {"expected_url": settings.voice_base_url}},
        )
        return

    start = getattr(container.voice_engine, "start", None)
    if start is not None:
        try:
            await start()
        except Exception as exc:
            log.warning("voice service did not answer", extra={"ctx": {"error": str(exc)}})

    service, models = await ensure_voice_service(
        settings.voice_base_url, PROJECT_ROOT, autostart=True
    )
    state.service = service
    state.models = models
    if models is None:
        log.warning(
            "nothing answers the voice address and no service could be started; "
            "spoken commands will be reported as unavailable, typed and Telegram "
            "commands are unaffected",
            extra={"ctx": {"url": settings.voice_base_url}},
        )
        return
    log.info(
        "voice service ready",
        extra={
            "ctx": {
                "url": settings.voice_base_url,
                "started_here": service is not None,
                "engines": models,
            }
        },
    )


async def _stop_voice(container: Container, state: VoiceState) -> None:
    """Close the voice pipeline and stop a service this backend started.

    Args:
        container: Assembled dependency graph.
        state: Remembered voice service.

    Returns:
        None.
    """
    if state.service is not None:
        state.service.stop()
        state.service = None
    stop = getattr(container.voice_engine, "stop", None)
    if stop is not None:
        await stop()


def _build_bot_runner(settings: Settings, container: Container) -> TelegramBotRunner | None:
    if not settings.telegram_active:
        return None
    handler = TelegramCommandsHandler(
        container.process_user_command,
        container.authenticate_user,
    )
    return TelegramBotRunner(
        bot_token=settings.telegram_bot_token,
        on_text=handler.handle,
        allowed_chat_id=settings.telegram_chat_id,
    )
