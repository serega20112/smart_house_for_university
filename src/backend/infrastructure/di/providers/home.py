"""Дом: приёмник сообщений плат, раздатчик фактов и путь любого изменения железа."""

from __future__ import annotations

from dishka import Provider, Scope, alias, provide

from backend.application.interface.queries.automation_queries import AutomationQueries
from backend.application.interface.queries.device_queries import DeviceQueries
from backend.application.interface.queries.scenario_queries import ScenarioQueries
from backend.application.interface.services.board_gateway import BoardGateway
from backend.application.interface.services.board_report import BoardReport
from backend.application.interface.services.clock import Clock
from backend.application.interface.services.domain_event_dispatcher import DomainEventDispatcher
from backend.application.interface.services.home_device_directory import HomeDeviceDirectory
from backend.application.interface.services.home_state_store import HomeStateStore
from backend.application.interface.services.notification_factory import NotificationFactory
from backend.application.interface.services.realtime_publisher import RealtimePublisher
from backend.application.interface.services.user_notifier import UserNotifier
from backend.application.interface.unit_of_work.home import HomeUnitOfWorkFactory
from backend.application.services.device_control import DeviceControlService
from backend.application.services.home_provisioning import HomeProvisioning
from backend.application.services.home_state_service import HomeStateService
from backend.application.services.manual_override_reaction import ManualOverrideReaction
from backend.application.services.reaction_dispatcher import ReactionDispatcher
from backend.application.use_cases.home.read_home_snapshot import ReadHomeSnapshotUseCase
from backend.config.settings import Settings
from backend.domain.policies.device_selector import DeviceSelector

APP = Scope.APP
REQUEST = Scope.REQUEST


class HomeProvider(Provider):
    """Один дом: его живое состояние, его реакции и его исполнительный путь."""

    report = alias(source=HomeStateService, provides=BoardReport)
    events = alias(source=ReactionDispatcher, provides=DomainEventDispatcher)

    @provide(scope=APP)
    def home_state_service(
        self,
        state_store: HomeStateStore,
        realtime: RealtimePublisher,
        notifier: UserNotifier,
        notifications: NotificationFactory,
        clock: Clock,
        devices_of_home: HomeDeviceDirectory,
    ) -> HomeStateService:
        """Собирает приёмник всех входящих сообщений плат."""
        return HomeStateService(
            state_store=state_store,
            realtime=realtime,
            notifier=notifier,
            notifications=notifications,
            clock=clock,
            devices_of_home=devices_of_home,
        )

    @provide(scope=APP)
    def reactions(
        self,
        home_uow: HomeUnitOfWorkFactory,
        state_store: HomeStateStore,
        clock: Clock,
        settings: Settings,
    ) -> ReactionDispatcher:
        """Собирает раздатчик фактов, которые записывают агрегаты."""
        return ReactionDispatcher(
            (
                HomeProvisioning(home_uow),
                ManualOverrideReaction(
                    state_store=state_store,
                    clock=clock,
                    override_minutes=settings.automation_manual_override_minutes,
                ),
            )
        )

    @provide(scope=APP)
    def device_control(
        self,
        home_uow: HomeUnitOfWorkFactory,
        boards: BoardGateway,
        state_store: HomeStateStore,
        realtime: RealtimePublisher,
        dispatcher: DomainEventDispatcher,
        clock: Clock,
        selector: DeviceSelector,
    ) -> DeviceControlService:
        """Собирает единственный путь любого изменения железа."""
        return DeviceControlService(
            home_uow,
            boards,
            state_store,
            realtime,
            dispatcher,
            clock,
            selector,
        )

    @provide(scope=REQUEST)
    def home_snapshot(
        self,
        state_store: HomeStateStore,
        device_queries: DeviceQueries,
        scenario_queries: ScenarioQueries,
        automation_queries: AutomationQueries,
        clock: Clock,
    ) -> ReadHomeSnapshotUseCase:
        """Собирает снимок дома для главного экрана."""
        return ReadHomeSnapshotUseCase(
            state_store, device_queries, scenario_queries, automation_queries, clock
        )
