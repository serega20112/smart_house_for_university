"""Switch every device at once."""

from __future__ import annotations

from dataclasses import dataclass

from smart_home_backend.application.dto.device import DeviceExecutionResult
from smart_home_backend.application.interface.unit_of_work import UnitOfWorkFactory
from smart_home_backend.application.services import DeviceExecutor, HomeRuntime
from smart_home_backend.domain.enums.device import Capability


@dataclass(frozen=True, slots=True)
class TurnAllResult:
    """Outcome of a switch all command.

    Args:
        results: One execution result per addressed device.

    Returns:
        None.
    """

    results: list[DeviceExecutionResult]

    @property
    def switched(self) -> list[DeviceExecutionResult]:
        """Return the devices that were actually switched.

        Returns:
            list[DeviceExecutionResult]: Successful execution results.
        """
        return [result for result in self.results if result.ok]


class TurnAllDevicesUseCase:
    """Applies one capability to every device that supports it."""

    def __init__(
        self,
        uow_factory: UnitOfWorkFactory,
        executor: DeviceExecutor,
        runtime: HomeRuntime,
        manual_override_minutes: int = 30,
    ) -> None:
        """Initialize the use case.

        Args:
            uow_factory: Factory producing units of work.
            executor: Executor turning capabilities into relay commands.
            runtime: Runtime state holding the manual override window.
            manual_override_minutes: How long automation stays suspended.

        Returns:
            None.
        """
        self._uow_factory = uow_factory
        self._executor = executor
        self._runtime = runtime
        self._manual_override_minutes = manual_override_minutes

    async def execute(self, on: bool) -> TurnAllResult:
        """Switch every device on or off.

        Args:
            on: True to switch everything on, False to switch everything off.

        Returns:
            TurnAllResult: Outcome of the command.
        """
        async with self._uow_factory() as uow:
            devices = list(await uow.devices.list_all())
        capability = Capability.ON if on else Capability.OFF
        results = await self._executor.apply_to_all(devices, capability)
        if any(result.ok for result in results):
            self._runtime.set_manual_override(self._manual_override_minutes)
        return TurnAllResult(results=results)
