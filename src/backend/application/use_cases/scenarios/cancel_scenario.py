"""Отменить сценарий по его идентификатору."""

from __future__ import annotations

from backend.application.errors import ScenarioNotFoundError
from backend.application.interface.unit_of_work.home import HomeUnitOfWorkFactory
from backend.application.services.scenarios.details import scenario_view
from backend.application.services.scenarios.settling import ScenarioSettler
from backend.domain.identifiers import ScenarioId, UserId
from backend.domain.value_objects.scenario.finish_reason import FinishReason
from backend.domain.value_objects.scenario.scenario_view import ScenarioView


class CancelScenarioUseCase:
    """Отдаёт сценарий, который человек больше не хочет."""

    def __init__(self, home_uow: HomeUnitOfWorkFactory, settler: ScenarioSettler) -> None:
        """Собирает сценарий отмены.

        Args:
            home_uow: Граница транзакции над конфигурацией дома.
            settler: Сворачивание сценария после финальной стадии.
        """
        self._home_uow = home_uow
        self._settler = settler

    async def execute(self, user_id: UserId, scenario_id: ScenarioId) -> ScenarioView:
        """Отменяет сценарий.

        Отмена идёт тем же путём, что и завершение: прямая запись в базу оставила
        бы железо переключённым, окно ручного приоритета — открытым, а сообщения о
        ходе — идущими, что человек справедливо назвал бы багом.

        Args:
            user_id: Владелец сценария.
            scenario_id: Идентификатор сценария.

        Returns:
            ScenarioView: Отменённый сценарий.

        Raises:
            ScenarioNotFoundError: Когда у аккаунта нет такого сценария.
            ScenarioAlreadyFinishedError: Когда сценарий уже завершился.
        """
        async with self._home_uow() as uow:
            scenario = await uow.scenarios.get(user_id, scenario_id)
            if scenario is None:
                raise ScenarioNotFoundError(scenario_id)
            devices = list(await uow.devices.list_all(user_id))
            scenario.cancel()
            await uow.scenarios.update(scenario)
        await self._settler.settle(scenario, devices, FinishReason.CANCELLED_BY_USER)
        return scenario_view(scenario)
