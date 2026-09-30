"""Automation engine keeping the climate inside the configured band.

One cycle reads the current values, asks the domain policy which demands exist,
resolves a device per demand through capabilities and executes it. The engine
holds no repository: the caller supplies the configuration, which makes it easy
to run from a scheduler and to cover with unit tests.
"""

from __future__ import annotations

from collections.abc import Sequence

from smart_home_backend.application.dto.automation import AutomationCycleResult
from smart_home_backend.application.dto.device import DeviceExecutionResult
from smart_home_backend.application.services.device_executor import DeviceExecutor
from smart_home_backend.application.services.home_runtime import HomeRuntime
from smart_home_backend.domain.entities.automation import AutomationSettings
from smart_home_backend.domain.entities.device import Device
from smart_home_backend.domain.enums.operation import OperationStatus
from smart_home_backend.domain.policies import (
    ClimateDemand,
    evaluate,
    find_device_for_capability,
)

SKIP_AUTOMATION_DISABLED = "automation_disabled"
SKIP_MANUAL_OVERRIDE = "manual_override"
SKIP_NO_SENSOR_DATA = "no_sensor_data"


class AutomationEngine:
    """Drives the climate devices according to the automation settings."""

    def __init__(self, runtime: HomeRuntime, executor: DeviceExecutor) -> None:
        """Initialize the engine.

        Args:
            runtime: Runtime state holding the current reading.
            executor: Executor performing the capability commands.

        Returns:
            None.
        """
        self._runtime = runtime
        self._executor = executor

    async def run_once(
        self, devices: Sequence[Device], settings: AutomationSettings
    ) -> AutomationCycleResult:
        """Run a single automation cycle.

        Args:
            devices: Configured devices, filtered inside the engine.
            settings: Current automation settings.

        Returns:
            AutomationCycleResult: What was skipped, demanded and performed.
        """
        if not settings.enabled:
            return AutomationCycleResult(skipped_reason=SKIP_AUTOMATION_DISABLED)
        if self._runtime.is_manual_override():
            return AutomationCycleResult(skipped_reason=SKIP_MANUAL_OVERRIDE)

        reading = self._runtime.reading
        if not reading.is_valid:
            return AutomationCycleResult(skipped_reason=SKIP_NO_SENSOR_DATA)

        demands = evaluate(settings, reading)
        actions: list[DeviceExecutionResult] = []
        for demand in demands:
            action = await self._handle_demand(demand, devices, settings)
            if action is not None:
                actions.append(action)

        status = OperationStatus.SUCCESS
        if not actions and any(
            action.status is not OperationStatus.SUCCESS for action in actions
        ):
            status = OperationStatus.UNSUPPORTED

        return AutomationCycleResult(
            status=status,
            demands=[demand.value for demand in demands],
            actions=actions,
        )

    async def _handle_demand(
        self,
        demand: ClimateDemand,
        devices: Sequence[Device],
        settings: AutomationSettings,
    ) -> DeviceExecutionResult | None:
        capability = demand.capability
        if capability is None:
            return None
        device = find_device_for_capability(
            devices, capability, settings=settings, only_automation=True
        )
        if device is None:
            return DeviceExecutionResult(status=OperationStatus.UNSUPPORTED)
        return await self._executor.apply(device, capability)
