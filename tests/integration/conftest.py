"""Fixtures wiring the application to an in-memory database."""

from __future__ import annotations

from collections.abc import AsyncIterator

import pytest
import pytest_asyncio

from smart_home_backend.application.dto.user import RegisterUserCommand
from smart_home_backend.application.interface.services import CommandOutcome
from smart_home_backend.config import Settings
from smart_home_backend.domain.value_objects.identity import UserId
from smart_home_backend.infrastructure.database import (
    SqlUnitOfWork,
    build_engine,
    build_session_factory,
    create_schema,
)
from smart_home_backend.infrastructure.di import build_container
from smart_home_backend.infrastructure.esp import EspGatewayAdapter
from smart_home_backend.infrastructure.logging_config import configure_logging

IN_MEMORY_URL = "sqlite+aiosqlite:///:memory:"
TEST_TOKEN_SECRET = "test-secret"


class RecordingEspGateway:
    """Physical gateway standing in for the board."""

    def __init__(self) -> None:
        self.commands: list[tuple[UserId, int, bool]] = []
        self.outcome = CommandOutcome(ok=True)
        self.state_requests: list[UserId] = []

    async def set_relay(self, user_id: UserId, channel: int, on: bool) -> CommandOutcome:
        self.commands.append((user_id, channel, on))
        return self.outcome

    async def request_state(self, user_id: UserId) -> None:
        self.state_requests.append(user_id)

    def go_offline(self) -> None:
        self.outcome = CommandOutcome(ok=False, error="esp_offline")

    def go_online(self) -> None:
        self.outcome = CommandOutcome(ok=True)


def build_test_settings() -> Settings:
    """Return settings pointing every adapter at a test friendly target.

    Returns:
        Settings: Configuration used by the test graph.
    """
    configure_logging("WARNING")
    configured = Settings()
    configured.database_url = IN_MEMORY_URL
    configured.esp_server_port = 0
    configured.telegram_enabled = False
    configured.nlp_allow_lexical_fallback = True
    configured.auth_token_secret = TEST_TOKEN_SECRET
    return configured


@pytest_asyncio.fixture
async def uow_factory() -> AsyncIterator[object]:
    engine = build_engine(IN_MEMORY_URL)
    await create_schema(engine)
    session_factory = build_session_factory(engine)
    yield lambda: SqlUnitOfWork(session_factory)
    await engine.dispose()


@pytest.fixture
def settings() -> Settings:
    return build_test_settings()


@pytest.fixture
def board(monkeypatch: pytest.MonkeyPatch) -> RecordingEspGateway:
    gateway = RecordingEspGateway()

    async def set_relay(_self, user_id: UserId, channel: int, on: bool) -> CommandOutcome:
        return await gateway.set_relay(user_id, channel, on)

    async def request_state(_self, user_id: UserId) -> None:
        await gateway.request_state(user_id)

    monkeypatch.setattr(EspGatewayAdapter, "set_relay", set_relay)
    monkeypatch.setattr(EspGatewayAdapter, "request_state", request_state)
    return gateway


@pytest_asyncio.fixture
async def container(settings: Settings, events, board) -> AsyncIterator[object]:
    graph = build_container(settings, events)
    await create_schema(graph.engine)
    yield graph
    await graph.engine.dispose()


@pytest_asyncio.fixture
async def account(container) -> AsyncIterator[UserId]:
    """Register one account and return its identifier.

    Args:
        container: Assembled dependency graph.

    Returns:
        UserId: Owner of the freshly created account.
    """
    session = await container.register_user.execute(
        RegisterUserCommand(
            email="vasya@example.com", password="super-secret-1", display_name="Вася"
        )
    )
    container.runtimes.for_user(session.user_id).set_esp_online(True)
    yield session.user_id
