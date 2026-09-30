"""Read the full home snapshot."""

from __future__ import annotations

from dataclasses import dataclass

from smart_home_backend.application.interface.unit_of_work import UnitOfWorkFactory
from smart_home_backend.application.services import HomeRuntime
from smart_home_backend.domain.entities.automation import AutomationSettings
from smart_home_backend.domain.entities.home import ClimateReading
from smart_home_backend.domain.entities.scenario import Scenario


@dataclass(frozen=True, slots=True)
class HomeSnapshot:
    """Everything the interface needs to render the state of the home.

    Args:
        reading: Current sensor reading.
        esp_online: Whether the board is reachable.
        manual_override: Whether automation is suspended by manual control.
        automation: Current automation settings.
        active_scenarios: Scenarios occupying the control priority.

    Returns:
        None.
    """

    reading: ClimateReading
    esp_online: bool
    manual_override: bool
    automation: AutomationSettings
    active_scenarios: list[Scenario]


class GetHomeSnapshotUseCase:
    """Assembles the live state of the home for the main screen."""

    def __init__(self, uow_factory: UnitOfWorkFactory, runtime: HomeRuntime) -> None:
        """Initialize the use case.

        Args:
            uow_factory: Factory producing units of work.
            runtime: Runtime state holding the live values.

        Returns:
            None.
        """
        self._uow_factory = uow_factory
        self._runtime = runtime

    async def execute(self) -> HomeSnapshot:
        """Return the current state of the home.

        Returns:
            HomeSnapshot: Snapshot combining live and stored state.
        """
        async with self._uow_factory() as uow:
            automation = await uow.automation.get()
            active_scenarios = list(await uow.scenarios.list_active())
        return HomeSnapshot(
            reading=self._runtime.reading,
            esp_online=self._runtime.esp_online,
            manual_override=self._runtime.is_manual_override(),
            automation=automation,
            active_scenarios=active_scenarios,
        )
