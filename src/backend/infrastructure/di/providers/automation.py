"""Автоматизация: один цикл, который сравнивает показания с требованиями."""

from __future__ import annotations

from dishka import Provider, Scope, provide

from backend.application.interface.services.clock import Clock
from backend.application.interface.services.domain_event_dispatcher import DomainEventDispatcher
from backend.application.interface.services.home_state_store import HomeStateStore
from backend.application.interface.services.realtime_publisher import RealtimePublisher
from backend.application.interface.unit_of_work.home import HomeUnitOfWorkFactory
from backend.application.services.automation_service import AutomationService
from backend.application.services.device_control import DeviceControlService
from backend.application.use_cases.automation.update_automation import UpdateAutomationUseCase
from backend.domain.policies.climate_policy import DemandCalculator
from backend.domain.policies.device_selector import DeviceSelector

APP = Scope.APP
REQUEST = Scope.REQUEST


class AutomationProvider(Provider):
    """Автоматика дома поверх единого исполнительного пути."""

    @provide(scope=APP)
    def automation(
        self,
        home_uow: HomeUnitOfWorkFactory,
        control: DeviceControlService,
        state_store: HomeStateStore,
        demands: DemandCalculator,
        selector: DeviceSelector,
        clock: Clock,
    ) -> AutomationService:
        """Собирает один цикл автоматизации дома."""
        return AutomationService(home_uow, control, state_store, demands, selector, clock)

    @provide(scope=REQUEST)
    def update_automation(
        self,
        home_uow: HomeUnitOfWorkFactory,
        realtime: RealtimePublisher,
        dispatcher: DomainEventDispatcher,
    ) -> UpdateAutomationUseCase:
        """Собирает изменение настройки автоматизации."""
        return UpdateAutomationUseCase(home_uow, realtime, dispatcher)
