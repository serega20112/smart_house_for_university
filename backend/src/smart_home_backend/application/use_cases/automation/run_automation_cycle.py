"""Run a single automation cycle."""

from __future__ import annotations

from smart_home_backend.application.dto.automation import AutomationCycleResult
from smart_home_backend.application.interface.unit_of_work import UnitOfWorkFactory
from smart_home_backend.application.services import AutomationEngine


class RunAutomationCycleUseCase:
    """Executes one automation cycle on behalf of the scheduler or the API."""

    def __init__(self, uow_factory: UnitOfWorkFactory, engine: AutomationEngine) -> None:
        """Initialize the use case.

        Args:
            uow_factory: Factory producing units of work.
            engine: Automation engine performing the cycle.

        Returns:
            None.
        """
        self._uow_factory = uow_factory
        self._engine = engine

    async def execute(self) -> AutomationCycleResult:
        """Load the configuration and run one cycle.

        Returns:
            AutomationCycleResult: What the cycle did.
        """
        async with self._uow_factory() as uow:
            devices = list(await uow.devices.list_all())
            settings = await uow.automation.get()
        return await self._engine.run_once(devices, settings)
