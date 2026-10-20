"""FastAPI application factory.

Builds the application with a single Dishka container, mounts the API router,
starts the board WebSocket transport in the lifespan and stops it on shutdown.

There is exactly one application serving every account. Nothing here is seeded
per user: a new home appears the moment a user registers, because registration
is what creates its devices, preferences and dashboard.
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from dishka.integrations.fastapi import setup_dishka
from fastapi import FastAPI

from smart_home.application.ports.services import SessionTokenIssuer
from smart_home.bootstrap.version import version_of
from smart_home.config import Settings
from smart_home.infrastructure.di.container import make_container
from smart_home.infrastructure.esp.connection import EspConnection
from smart_home.infrastructure.logging import configure_logging, get_logger
from smart_home.infrastructure.redis.event_broker import RedisSubscriber
from smart_home.presentation.api import api_router
from smart_home.presentation.api.errors import install_error_handlers
from smart_home.presentation.api.messages import CommandReplyComposer, NotificationFactoryImpl
from smart_home.presentation.web.frontend import mount_frontend
from smart_home.presentation.websocket.endpoint import router as websocket_router
from smart_home.presentation.websocket.hub import WebSocketHub

log = get_logger("app")


def create_app(settings: Settings | None = None) -> FastAPI:
    """Build the FastAPI application.

    Args:
        settings: Configuration to build the graph from, defaults to the
            environment configuration.

    Returns:
        FastAPI: Configured application.
    """
    settings = settings or Settings()
    configure_logging(settings.server.log_level)

    container = make_container(
        settings,
        notifications=NotificationFactoryImpl(),
        composer=CommandReplyComposer(),
    )

    app = FastAPI(
        title=settings.app_name,
        version=version_of().value,
    )
    app.state.container = container

    setup_dishka(container=container, app=app)

    app.include_router(api_router, prefix="/api")
    app.include_router(websocket_router)
    install_error_handlers(app)
    mount_frontend(app)

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        """Start and stop every subsystem of the application.

        Args:
            app: Application being started.

        Yields:
            None while the application is running.
        """
        connection = await container.get(EspConnection)
        subscriber = await container.get(RedisSubscriber)
        hub = WebSocketHub(subscriber)
        app.state.hub = hub
        app.state.tokens = await container.get(SessionTokenIssuer)
        await connection.start()
        try:
            yield
        finally:
            await connection.stop()
            await hub.stop()
            await container.close()

    app.router.lifespan_context = lifespan

    return app
