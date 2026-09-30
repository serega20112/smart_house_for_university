"""Advance the active scenarios."""

from __future__ import annotations

from smart_home_backend.application.interface.unit_of_work import UnitOfWorkFactory
from smart_home_backend.application.services import ScenarioEngine


class TickScenariosUseCase:
    """Moves every active scenario forward by one step."""

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

    async def execute(self) -> None:
        """Run one scenario tick.

        Returns:
            None.
        """
        async with self._uow_factory() as uow:
            await self._engine.tick(
                active=list(await uow.scenarios.list_active()),
                devices=list(await uow.devices.list_all()),
                persist=uow.scenarios.save,
            )
