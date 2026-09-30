"""Run a climate capability chosen by device selection."""

from __future__ import annotations

from smart_home_backend.application.dto.device import DeviceExecutionResult
from smart_home_backend.application.interface.unit_of_work import UnitOfWorkFactory
from smart_home_backend.application.services import DeviceExecutor, HomeRuntime
from smart_home_backend.domain.enums.device import Capability


class RunClimateCapabilityUseCase:
    """Applies a climate capability to the first device that supports it."""

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

    async def execute(self, capability: Capability) -> DeviceExecutionResult:
        """Apply the capability to a matching device.

        Args:
            capability: Capability to perform, for example cooling.

        Returns:
            DeviceExecutionResult: Outcome of the command.
        """
        async with self._uow_factory() as uow:
            devices = list(await uow.devices.list_all())
        result = await self._executor.apply_first_matching(devices, capability)
        if result.ok:
            self._runtime.set_manual_override(self._manual_override_minutes)
        return result
