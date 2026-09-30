"""FastAPI application factory.

Creates the schema, seeds the default devices, starts the board connection, the
background loops and the Telegram bot, and shuts everything down cleanly.
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from smart_home_backend.config import Settings, settings as default_settings
from smart_home_backend.domain.entities.device import Device
from smart_home_backend.domain.enums.device import Capability, DeviceType
from smart_home_backend.infrastructure.database import create_schema
from smart_home_backend.infrastructure.di import Container, build_container
from smart_home_backend.infrastructure.logging_config import configure_logging, get_logger
from smart_home_backend.infrastructure.telegram import TelegramBotRunner
from smart_home_backend.presentation.api import api_router
from smart_home_backend.presentation.telegram import TelegramCommandsHandler
from smart_home_backend.presentation.websocket import WebSocketHub
from smart_home_backend.presentation.websocket.endpoint import router as websocket_router
from smart_home_backend.presentation.web import mount_frontend

log = get_logger("app")

DEFAULT_DEVICES: tuple[tuple[str, DeviceType, int, frozenset[Capability], bool], ...] = (
    ("Основной свет", DeviceType.LIGHT, 1, frozenset({Capability.ON, Capability.OFF}), False),
    (
        "Увлажнитель",
        DeviceType.HUMIDIFIER,
        2,
        frozenset({Capability.ON, Capability.OFF}),
        True,
    ),
    ("Вентилятор", DeviceType.FAN, 3, frozenset({Capability.ON, Capability.OFF}), True),
    ("Обогреватель", DeviceType.HEATER, 5, frozenset({Capability.ON, Capability.OFF}), True),
    (
        "Кондиционер",
        DeviceType.AIR_CONDITIONER,
        6,
        frozenset({Capability.OFF, Capability.COOL, Capability.HEAT}),
        True,
    ),
)


async def seed_default_devices(container: Container) -> None:
    """Create the six default devices on the first start.

    Args:
        container: Assembled dependency graph.

    Returns:
        None.
    """
    async with container.uow_factory() as uow:
        if await uow.devices.list_all():
            return
        for name, device_type, channel, capabilities, automation_enabled in DEFAULT_DEVICES:
            await uow.devices.save(
                Device(
                    id=0,
                    name=name,
                    type=device_type,
                    physical_channel=channel,
                    capabilities=capabilities,
                    enabled=True,
                    automation_enabled=automation_enabled,
                )
            )
    log.info("Default devices seeded", extra={"ctx": {"count": len(DEFAULT_DEVICES)}})


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
    container = build_container(settings, hub)
    bot_runner = _build_bot_runner(settings, container)

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        """Start and stop every subsystem of the application.

        Args:
            app: Application being started.

        Returns:
            AsyncIterator[None]: Lifespan iterator.
        """
        await create_schema(container.engine)
        await seed_default_devices(container)
        await container.esp_connection.start()
        await container.scheduler.start()
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
            await container.scheduler.stop()
            await container.esp_connection.stop()
            await container.engine.dispose()
            log.info("Smart Home backend stopped")

    app = FastAPI(title="Smart Home Backend", version="1.0.0", lifespan=lifespan)
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


def _build_bot_runner(settings: Settings, container: Container) -> TelegramBotRunner | None:
    if not settings.telegram_active:
        return None
    handler = TelegramCommandsHandler(container.process_user_command)
    return TelegramBotRunner(
        bot_token=settings.telegram_bot_token,
        on_text=handler.handle,
        allowed_chat_id=settings.telegram_chat_id,
    )
