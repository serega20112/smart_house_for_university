"""Cancel a timed scenario."""

from __future__ import annotations

from smart_home_backend.application.interface.unit_of_work import UnitOfWorkFactory
from smart_home_backend.domain.entities.scenario import Scenario
from smart_home_backend.domain.enums.operation import OperationStatus
from smart_home_backend.domain.enums.scenario import ScenarioStatus


class CancelScenarioUseCase:
    """Marks a scenario as cancelled."""

    def __init__(self, uow_factory: UnitOfWorkFactory) -> None:
        """Initialize the use case.

        Args:
            uow_factory: Factory producing units of work.

        Returns:
            None.
        """
        self._uow_factory = uow_factory

    async def execute(self, scenario_id: int) -> tuple[OperationStatus, Scenario | None]:
        """Cancel a pending or running scenario.

        A scenario that already finished cannot be cancelled, so the user gets
        a clear answer instead of a second cancellation.

        Args:
            scenario_id: Identifier of the scenario.

        Returns:
            tuple[OperationStatus, Scenario | None]: Status and the cancelled scenario.
        """
        async with self._uow_factory() as uow:
            scenario = await uow.scenarios.get(scenario_id)
            if scenario is None or not scenario.is_active:
                return OperationStatus.NOT_FOUND, None
            scenario.status = ScenarioStatus.CANCELLED
            saved = await uow.scenarios.save(scenario)
        return OperationStatus.SUCCESS, saved
