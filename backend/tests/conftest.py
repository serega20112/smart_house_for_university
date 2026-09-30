"""Shared test fixtures."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from smart_home_backend.application.interface.services import (
    Clock,
    CommandOutcome,
    EspGateway,
    EventBus,
    Notifier,
)
from smart_home_backend.domain.entities.automation import AutomationSettings
from smart_home_backend.domain.entities.device import Device
from smart_home_backend.domain.enums.device import Capability, DeviceType

BASE_TIME = datetime(2026, 5, 1, 12, 0, tzinfo=timezone.utc)


class FrozenClock(Clock):
    """Clock returning a controlled moment."""

    def __init__(self, moment: datetime = BASE_TIME) -> None:
        self._moment = moment

    def now(self) -> datetime:
        return self._moment

    def advance(self, **delta: float) -> None:
        self._moment += timedelta(**delta)


class RecordingEventBus(EventBus):
    """Event bus keeping every published event in memory."""

    def __init__(self) -> None:
        self.events: list[tuple[str, dict]] = []

    async def publish(self, event_type: str, payload: dict) -> None:
        self.events.append((event_type, payload))

    def types(self) -> list[str]:
        return [event_type for event_type, _payload in self.events]


class RecordingNotifier(Notifier):
    """Notifier keeping every notification in memory."""

    def __init__(self) -> None:
        self.messages: list[str] = []

    async def notify(self, text: str) -> None:
        self.messages.append(text)


class FakeEspGateway(EspGateway):
    """Gateway recording relay commands and returning a scripted outcome."""

    def __init__(self, outcome: CommandOutcome | None = None) -> None:
        self._outcome = outcome or CommandOutcome(ok=True)
        self.commands: list[tuple[int, bool]] = []
        self.state_requests = 0

    async def set_relay(self, channel: int, on: bool) -> CommandOutcome:
        self.commands.append((channel, on))
        return self._outcome

    async def request_state(self) -> None:
        self.state_requests += 1


@pytest.fixture
def clock() -> FrozenClock:
    return FrozenClock()


@pytest.fixture
def events() -> RecordingEventBus:
    return RecordingEventBus()


@pytest.fixture
def notifier() -> RecordingNotifier:
    return RecordingNotifier()


@pytest.fixture
def esp() -> FakeEspGateway:
    return FakeEspGateway()


@pytest.fixture
def light() -> Device:
    return Device(
        id=1,
        name="Основной свет",
        type=DeviceType.LIGHT,
        physical_channel=1,
        capabilities=frozenset({Capability.ON, Capability.OFF}),
        automation_enabled=False,
    )


@pytest.fixture
def air_conditioner() -> Device:
    return Device(
        id=2,
        name="Кондиционер",
        type=DeviceType.AIR_CONDITIONER,
        physical_channel=4,
        capabilities=frozenset({Capability.OFF, Capability.COOL, Capability.HEAT}),
    )


@pytest.fixture
def automation() -> AutomationSettings:
    return AutomationSettings(
        enabled=True,
        target_temperature=22.0,
        temperature_tolerance=1.0,
        target_humidity=45.0,
        humidity_tolerance=5.0,
    )
