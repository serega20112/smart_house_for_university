"""Create a timed scenario."""

from __future__ import annotations

from smart_home_backend.application.dto.scenario import CreateScenarioCommand
from smart_home_backend.application.interface.unit_of_work import UnitOfWorkFactory
from smart_home_backend.application.services import ScenarioEngine
from smart_home_backend.domain.entities.scenario import Scenario


class CreateScenarioUseCase:
    """Schedules a deferred climate or device action."""

    def __init__(self, uow_factory: UnitOfWorkFactory, engine: ScenarioEngine) -> None:
        """Initialize the use case.

        Args:
            uow_factory: Factory producing units of work.
            engine: Scenario engine owning the lifecycle.

        Returns:
            None.
        """
        self._uow_factory = uow_factory
        self._engine = engine

    async def execute(self, command: CreateScenarioCommand) -> Scenario:
        """Store a new pending scenario.

        Args:
            command: Scenario description.

        Returns:
            Scenario: Stored scenario including its identifier.
        """
        async with self._uow_factory() as uow:
            return await self._engine.create(
                delay_minutes=command.delay_minutes,
                capability=command.capability,
                target_temperature=command.target_temperature,
                target=command.target,
                completion_behavior=command.completion_behavior,
                persist=uow.scenarios.save,
            )
