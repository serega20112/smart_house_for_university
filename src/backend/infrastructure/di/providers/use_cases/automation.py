"""Автоматизация: один цикл, который сравнивает показания с требованиями."""

from __future__ import annotations

from dishka import Provider, Scope, provide

from backend.application.interfaces.services.messaging.domain_event_dispatcher import (
    DomainEventDispatcher,
)
from backend.application.interfaces.services.messaging.realtime_publisher import RealtimePublisher
from backend.application.interfaces.services.state.home_state_store import HomeStateStore
from backend.application.interfaces.services.system.clock import Clock
from backend.application.interfaces.unit_of_work.home import HomeUnitOfWorkFactory
from backend.application.services.automation_service import AutomationService
from backend.application.services.device_control import DeviceControlService
from backend.application.use_cases.automation.update_automation import UpdateAutomationUseCase
from backend.domain.policies.climate_policy import DemandCalculator
from backend.domain.policies.device_selector import DeviceSelector

APP = Scope.APP
REQUEST = Scope.REQUEST


class AutomationUseCaseProvider(Provider):
    """Автоматика дома поверх единого исполнительного пути."""

    @provide(scope=APP)
    def automation(
        self,
        home_uow: HomeUnitOfWorkFactory,
        control: DeviceControlService,
        state_store: HomeStateStore,
        clock: Clock,
    ) -> AutomationService:
        """Собирает один цикл автоматизации дома.

        Доменные решатели строятся здесь напрямую: у них нет ни зависимостей, ни
        состояния, поэтому провайдер домена им не нужен.
        """
        return AutomationService(
            home_uow, control, state_store, DemandCalculator(), DeviceSelector(), clock
        )

    @provide(scope=REQUEST)
    def update_automation(
        self,
        home_uow: HomeUnitOfWorkFactory,
        realtime: RealtimePublisher,
        dispatcher: DomainEventDispatcher,
    ) -> UpdateAutomationUseCase:
        """Собирает изменение настройки автоматизации."""
        return UpdateAutomationUseCase(home_uow, realtime, dispatcher)
