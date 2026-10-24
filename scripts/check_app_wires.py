"""Проверка связки: конфигурация читается, граф собирается целиком, маршруты на месте.

Контейнер строится лениво, поэтому одной сборки приложения мало: провайдер с
неподходящей сигнатурой или забытая зависимость всплывают только когда ключ
впервые попросили. Здесь запрашиваются все связываемые узлы графа, а кодировщик
предложений подменяется заглушкой, чтобы проверка не скачивала модель.

Запуск из корня проекта: python scripts/check_app_wires.py
"""

from __future__ import annotations

import asyncio
import sys
from collections.abc import Sequence
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

import httpx
from dishka import make_async_container
from sqlalchemy.ext.asyncio import AsyncEngine, async_sessionmaker

from backend.application.interfaces.queries.account_queries import AccountQueries
from backend.application.interfaces.queries.automation_queries import AutomationQueries
from backend.application.interfaces.queries.board_queries import BoardQueries
from backend.application.interfaces.queries.device_queries import DeviceQueries
from backend.application.interfaces.queries.scenario_queries import ScenarioQueries
from backend.application.interfaces.services.boards.board_gateway import BoardGateway
from backend.application.interfaces.services.boards.board_report import BoardReport
from backend.application.interfaces.services.language.command_understanding import (
    CommandUnderstandingPort,
)
from backend.application.interfaces.services.language.embedder import Embedder
from backend.application.interfaces.services.messaging.domain_event_dispatcher import (
    DomainEventDispatcher,
)
from backend.application.interfaces.services.messaging.notification_factory import (
    NotificationFactory,
)
from backend.application.interfaces.services.messaging.realtime_publisher import RealtimePublisher
from backend.application.interfaces.services.messaging.user_notifier import UserNotifier
from backend.application.interfaces.services.security.password_hasher import PasswordHasher
from backend.application.interfaces.services.security.session_token_issuer import SessionTokenIssuer
from backend.application.interfaces.services.state.home_device_directory import HomeDeviceDirectory
from backend.application.interfaces.services.state.home_state_store import HomeStateStore
from backend.application.interfaces.services.system.clock import Clock
from backend.application.interfaces.services.system.distributed_lock import DistributedLock
from backend.application.interfaces.unit_of_work.account import AccountUnitOfWorkFactory
from backend.application.interfaces.unit_of_work.board_onboarding import (
    BoardOnboardingUnitOfWorkFactory,
)
from backend.application.interfaces.unit_of_work.home import HomeUnitOfWorkFactory
from backend.application.services.automation_service import AutomationService
from backend.application.services.board_onboarding import BoardOnboardingService
from backend.application.services.command_dispatcher import CommandDispatcher
from backend.application.services.device_control import DeviceControlService
from backend.application.services.home_state_service import HomeStateService
from backend.application.services.language.understanding import ReferencePhraseSeeder
from backend.application.services.reaction_dispatcher import ReactionDispatcher
from backend.application.services.scenarios.advancing import ScenarioAdvancer
from backend.application.services.scenarios.settling import ScenarioSettler
from backend.application.use_cases.accounts.authenticate_account import AuthenticateAccountUseCase
from backend.application.use_cases.accounts.register_account import RegisterAccountUseCase
from backend.application.use_cases.automation.update_automation import UpdateAutomationUseCase
from backend.application.use_cases.boards.claim_board import ClaimBoardUseCase
from backend.application.use_cases.boards.configure_board_network import (
    ConfigureBoardNetworkUseCase,
)
from backend.application.use_cases.boards.list_boards import ListBoardsUseCase
from backend.application.use_cases.boards.list_claims import ListBoardClaimsUseCase
from backend.application.use_cases.boards.pair_board import PairBoardUseCase
from backend.application.use_cases.boards.read_board_network import ReadBoardNetworkUseCase
from backend.application.use_cases.boards.revoke_board import RevokeBoardUseCase
from backend.application.use_cases.commands.cancel_scenario import CancelScenarioCommandUseCase
from backend.application.use_cases.commands.describe_home import DescribeHomeCommandUseCase
from backend.application.use_cases.commands.read_humidity import ReadHumidityCommandUseCase
from backend.application.use_cases.commands.read_temperature import ReadTemperatureCommandUseCase
from backend.application.use_cases.commands.run_capability import RunCapabilityCommandUseCase
from backend.application.use_cases.commands.schedule_scenario import ScheduleScenarioCommandUseCase
from backend.application.use_cases.commands.set_humidity_target import (
    SetHumidityTargetCommandUseCase,
)
from backend.application.use_cases.commands.set_temperature_target import (
    SetTemperatureTargetCommandUseCase,
)
from backend.application.use_cases.commands.switch_all import SwitchAllDevicesCommandUseCase
from backend.application.use_cases.commands.switch_device import SwitchDeviceCommandUseCase
from backend.application.use_cases.devices.create_device import CreateDeviceUseCase
from backend.application.use_cases.devices.delete_device import DeleteDeviceUseCase
from backend.application.use_cases.devices.list_devices import ListDevicesUseCase
from backend.application.use_cases.devices.switch_all_devices import SwitchAllDevicesUseCase
from backend.application.use_cases.devices.switch_device import SwitchDeviceUseCase
from backend.application.use_cases.devices.update_device import UpdateDeviceUseCase
from backend.application.use_cases.home.read_home_snapshot import ReadHomeSnapshotUseCase
from backend.application.use_cases.personalization.read_dashboard import ReadDashboardUseCase
from backend.application.use_cases.personalization.read_preferences import ReadPreferencesUseCase
from backend.application.use_cases.personalization.update_dashboard import UpdateDashboardUseCase
from backend.application.use_cases.personalization.update_preferences import (
    UpdatePreferencesUseCase,
)
from backend.application.use_cases.scenarios.cancel_scenario import CancelScenarioUseCase
from backend.application.use_cases.scenarios.list_scenarios import ListScenariosUseCase
from backend.application.use_cases.scenarios.schedule_scenario import ScheduleScenarioUseCase
from backend.config import Settings
from backend.infrastructure.brokers.chat_sessions import RedisChatSessionStore
from backend.infrastructure.brokers.event_broker import RedisSubscriber
from backend.infrastructure.di.dishka_container import PROVIDERS
from backend.infrastructure.esp.connection import EspConnection
from backend.infrastructure.security.link_tokens import TelegramLinkTokenIssuer
from backend.infrastructure.telegram.client import TelegramBotClient
from backend.presentation.app_factory import create_app
from backend.presentation.messages import NotificationFactoryImpl

APP_ENTRIES: tuple[Any, ...] = (
    Clock,
    PasswordHasher,
    SessionTokenIssuer,
    AsyncEngine,
    async_sessionmaker,
    httpx.AsyncClient,
    TelegramBotClient,
    TelegramLinkTokenIssuer,
    UserNotifier,
    RedisSubscriber,
    RedisChatSessionStore,
    HomeStateStore,
    RealtimePublisher,
    DistributedLock,
    AccountQueries,
    DeviceQueries,
    AutomationQueries,
    ScenarioQueries,
    BoardQueries,
    AccountUnitOfWorkFactory,
    HomeUnitOfWorkFactory,
    BoardOnboardingUnitOfWorkFactory,
    HomeDeviceDirectory,
    CommandUnderstandingPort,
    HomeStateService,
    BoardReport,
    ReactionDispatcher,
    DomainEventDispatcher,
    DeviceControlService,
    AutomationService,
    ScenarioSettler,
    ScenarioAdvancer,
    ScheduleScenarioUseCase,
    CancelScenarioUseCase,
    ReferencePhraseSeeder,
    BoardOnboardingService,
    EspConnection,
    BoardGateway,
    SwitchDeviceCommandUseCase,
    SwitchAllDevicesCommandUseCase,
    SetTemperatureTargetCommandUseCase,
    SetHumidityTargetCommandUseCase,
    RunCapabilityCommandUseCase,
    DescribeHomeCommandUseCase,
    ReadTemperatureCommandUseCase,
    ReadHumidityCommandUseCase,
    ScheduleScenarioCommandUseCase,
    CancelScenarioCommandUseCase,
    CommandDispatcher,
)

REQUEST_ENTRIES: tuple[Any, ...] = (
    RegisterAccountUseCase,
    AuthenticateAccountUseCase,
    CreateDeviceUseCase,
    UpdateDeviceUseCase,
    DeleteDeviceUseCase,
    ListDevicesUseCase,
    SwitchDeviceUseCase,
    SwitchAllDevicesUseCase,
    ReadHomeSnapshotUseCase,
    UpdateAutomationUseCase,
    ListScenariosUseCase,
    ClaimBoardUseCase,
    PairBoardUseCase,
    RevokeBoardUseCase,
    ListBoardsUseCase,
    ListBoardClaimsUseCase,
    ConfigureBoardNetworkUseCase,
    ReadBoardNetworkUseCase,
    ReadPreferencesUseCase,
    UpdatePreferencesUseCase,
    ReadDashboardUseCase,
    UpdateDashboardUseCase,
)


class PlaceholderEmbedder:
    """Кодировщик без модели: проверка сверяет связи графа, а не качество векторов."""

    def encode(self, texts: Sequence[str]) -> list[list[float]]:
        """Возвращает по одному нулевому измерению на фразу."""
        return [[0.0] for _ in texts]


async def check_graph() -> list[str]:
    """Пробует собрать каждый узел графа и перечисляет то, что не собралось.

    Returns:
        list[str]: Строки вида «узел — причина отказа», пустые когда граф цел.
    """
    container = make_async_container(
        *PROVIDERS,
        context={
            Settings: Settings(),
            NotificationFactory: NotificationFactoryImpl(),
            Embedder: PlaceholderEmbedder(),
        },
    )
    failures: list[str] = []
    for key in APP_ENTRIES:
        try:
            await container.get(key)
        except Exception as error:
            failures.append(f"{getattr(key, '__name__', key)}: {type(error).__name__}: {error}")
    async with container() as request_container:
        for key in REQUEST_ENTRIES:
            try:
                await request_container.get(key)
            except Exception as error:
                failures.append(f"{getattr(key, '__name__', key)}: {type(error).__name__}: {error}")
    await container.close()
    return failures


def check_routes() -> list[str]:
    """Собирает приложение и возвращает опубликованные пути.

    Returns:
        list[str]: Путы OpenAPI собранного приложения.
    """
    settings = Settings()
    print(f"app: {settings.app_name} on {settings.app_host}:{settings.app_port}")
    app = create_app(settings)
    return sorted(app.openapi()["paths"])


async def main() -> int:
    """Собрать граф целиком и показать, что приложение опубликовало маршруты.

    Returns:
        int: Ноль, когда граф собрался и маршруты на месте.
    """
    paths = check_routes()
    print(f"openapi paths: {len(paths)}")
    for path in paths:
        print(f"  {path}")

    failures = await check_graph()
    total = len(APP_ENTRIES) + len(REQUEST_ENTRIES)
    print(f"graph entries: {total}, failed: {len(failures)}")
    for failure in failures:
        print(f"  ! {failure}")
    return 0 if paths and not failures else 1


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
