"""Set a device mode."""

from __future__ import annotations

from smart_home_backend.application.dto.device import DeviceExecutionResult
from smart_home_backend.application.interface.unit_of_work import UnitOfWorkFactory
from smart_home_backend.application.services import DeviceExecutor, HomeRuntime
from smart_home_backend.domain.enums.device import Capability
from smart_home_backend.domain.enums.operation import OperationStatus


class SetDeviceModeUseCase:
    """Applies an explicit capability such as cooling or heating."""

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

    async def execute(self, device_id: int, mode: Capability) -> DeviceExecutionResult:
        """Switch a device into the requested mode.

        Args:
            device_id: Identifier of the device.
            mode: Capability to apply.

        Returns:
            DeviceExecutionResult: Outcome of the command.
        """
        async with self._uow_factory() as uow:
            device = await uow.devices.get(device_id)
        if device is None:
            return DeviceExecutionResult(status=OperationStatus.NOT_FOUND)
        result = await self._executor.apply(device, mode)
        if result.ok:
            self._runtime.set_manual_override(self._manual_override_minutes)
        return result
