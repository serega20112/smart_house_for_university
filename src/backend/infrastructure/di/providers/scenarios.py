"""Сценарии: сворачивание, фоновый шаг, постановка, отмена и список."""

from __future__ import annotations

from dishka import Provider, Scope, provide

from backend.application.interface.queries.scenario_queries import ScenarioQueries
from backend.application.interface.services.clock import Clock
from backend.application.interface.services.domain_event_dispatcher import DomainEventDispatcher
from backend.application.interface.services.home_state_store import HomeStateStore
from backend.application.interface.services.notification_factory import NotificationFactory
from backend.application.interface.services.realtime_publisher import RealtimePublisher
from backend.application.interface.services.user_notifier import UserNotifier
from backend.application.interface.unit_of_work.home import HomeUnitOfWorkFactory
from backend.application.services.device_control import DeviceControlService
from backend.application.services.scenarios.advancing import ScenarioAdvancer
from backend.application.services.scenarios.settling import ScenarioSettler
from backend.application.use_cases.scenarios.cancel_scenario import CancelScenarioUseCase
from backend.application.use_cases.scenarios.list_scenarios import ListScenariosUseCase
from backend.application.use_cases.scenarios.schedule_scenario import ScheduleScenarioUseCase
from backend.config.settings import Settings

APP = Scope.APP
REQUEST = Scope.REQUEST


class ScenarioProvider(Provider):
    """Всё, что происходит с запланированным действием дома."""

    @provide(scope=APP)
    def scenario_settler(
        self,
        control: DeviceControlService,
        realtime: RealtimePublisher,
        dispatcher: DomainEventDispatcher,
        notifier: UserNotifier,
        notifications: NotificationFactory,
    ) -> ScenarioSettler:
        """Собирает сворачивание сценария."""
        return ScenarioSettler(control, realtime, dispatcher, notifier, notifications)

    @provide(scope=APP)
    def scenario_advancer(
        self,
        home_uow: HomeUnitOfWorkFactory,
        control: DeviceControlService,
        state_store: HomeStateStore,
        realtime: RealtimePublisher,
        dispatcher: DomainEventDispatcher,
        notifier: UserNotifier,
        notifications: NotificationFactory,
        clock: Clock,
        settler: ScenarioSettler,
        settings: Settings,
    ) -> ScenarioAdvancer:
        """Собирает фоновый шаг сценариев дома."""
        return ScenarioAdvancer(
            home_uow,
            control,
            state_store,
            realtime,
            dispatcher,
            notifier,
            notifications,
            clock,
            settler,
            settings.automation_scenario_summary_ttl_sec,
        )

    @provide(scope=APP)
    def schedule_scenario(
        self,
        home_uow: HomeUnitOfWorkFactory,
        realtime: RealtimePublisher,
        dispatcher: DomainEventDispatcher,
        clock: Clock,
    ) -> ScheduleScenarioUseCase:
        """Собирает постановку сценария."""
        return ScheduleScenarioUseCase(home_uow, realtime, dispatcher, clock)

    @provide(scope=APP)
    def cancel_scenario(
        self, home_uow: HomeUnitOfWorkFactory, settler: ScenarioSettler
    ) -> CancelScenarioUseCase:
        """Собирает отмену сценария."""
        return CancelScenarioUseCase(home_uow, settler)

    @provide(scope=REQUEST)
    def list_scenarios(self, queries: ScenarioQueries) -> ListScenariosUseCase:
        """Собирает список сценариев."""
        return ListScenariosUseCase(queries)
