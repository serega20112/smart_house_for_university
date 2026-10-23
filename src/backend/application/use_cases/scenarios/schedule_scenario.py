"""Поставить сценарий, который ждёт своего момента."""

from __future__ import annotations

from backend.application.dto.scenario.schedule_scenario_command import ScheduleScenarioCommand
from backend.application.interface.services.clock import Clock
from backend.application.interface.services.domain_event_dispatcher import DomainEventDispatcher
from backend.application.interface.services.realtime_publisher import RealtimePublisher
from backend.application.interface.unit_of_work.home import HomeUnitOfWorkFactory
from backend.application.services.scenarios.details import scenario_payload, scenario_view
from backend.domain.aggregates.scenario.scenario import Scenario
from backend.domain.events import EventName
from backend.domain.identifiers import UserId
from backend.domain.value_objects.scenario.scenario_view import ScenarioView


class ScheduleScenarioUseCase:
    """Откладывает обещание дома на названное время."""

    def __init__(
        self,
        home_uow: HomeUnitOfWorkFactory,
        realtime: RealtimePublisher,
        dispatcher: DomainEventDispatcher,
        clock: Clock,
    ) -> None:
        """Собирает сценарий постановки.

        Args:
            home_uow: Граница транзакции над конфигурацией дома.
            realtime: Отправитель событий открытым клиентам.
            dispatcher: Раздатчик записанных фактов подписчикам.
            clock: Источник текущего момента.
        """
        self._home_uow = home_uow
        self._realtime = realtime
        self._dispatcher = dispatcher
        self._clock = clock

    async def execute(self, user_id: UserId, command: ScheduleScenarioCommand) -> ScenarioView:
        """Сохраняет сценарий, ожидающий старта.

        Args:
            user_id: Владелец сценария.
            command: Отложенное действие, которое попросил человек.

        Returns:
            ScenarioView: Сохранённый сценарий.
        """
        async with self._home_uow() as uow:
            scenario = Scenario.schedule(
                user_id=user_id,
                created_at=self._clock.now(),
                delay_minutes=command.delay_minutes,
                actions=(command.action,),
                target=command.target,
                completion_behavior=command.completion_behavior,
                duration_minutes=command.duration_minutes,
            )
            await uow.scenarios.add(scenario)
        await self._realtime.publish(
            user_id, EventName.SCENARIO_SCHEDULED, scenario_payload(scenario)
        )
        await self._dispatcher.dispatch(scenario.pull_events())
        return scenario_view(scenario)
