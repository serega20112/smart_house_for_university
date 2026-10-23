"""Keeping the climate inside the band the user configured.

One cycle reads the current values, asks the model which demands they produce,
resolves a device per demand and performs it. The cycle runs for one home at a time,
so every account stays independent even though one worker serves all of them.

The service never opens a transaction for the whole cycle: the configuration is read
once, then every command runs against the hardware without holding a database
connection open.
"""

from __future__ import annotations

from collections.abc import Sequence

from backend.application.errors import BoardUnreachableError
from backend.application.interface.services.clock import Clock
from backend.application.interface.services.home_state_store import HomeStateStore
from backend.application.interface.unit_of_work.home import HomeUnitOfWorkFactory
from backend.application.services.device_control import DeviceControlService
from backend.domain.aggregates.automation.automation_settings import AutomationSettings
from backend.domain.aggregates.device.device import Device
from backend.domain.identifiers import UserId
from backend.domain.policies.climate_policy import ClimateDemand, DemandCalculator
from backend.domain.policies.device_selector import DeviceSelector
from backend.domain.value_objects.automation.automation_cycle_report import AutomationCycleReport
from backend.domain.value_objects.climate.skip_reason import SkipReason


class AutomationService:
    """Runs one automation cycle of a home."""

    def __init__(
        self,
        home_uow: HomeUnitOfWorkFactory,
        control: DeviceControlService,
        state_store: HomeStateStore,
        demands: DemandCalculator,
        selector: DeviceSelector,
        clock: Clock,
    ) -> None:
        """Initialize the service.

        Args:
            home_uow: Factory producing transactions over the configuration.
            control: Service performing capabilities against the hardware.
            state_store: Durable home of the volatile state.
            demands: Model component deciding what the climate is asking for.
            selector: Domain resolver of devices by capability.
            clock: Source of the current time.

        Returns:
            None.
        """
        self._home_uow = home_uow
        self._control = control
        self._state_store = state_store
        self._demands = demands
        self._selector = selector
        self._clock = clock

    async def run_cycle(self, user_id: UserId) -> AutomationCycleReport:
        """Run one cycle and report what it did.

        Args:
            user_id: Owner whose home is being automated.

        Returns:
            AutomationCycleReport: Demands that were carried out, or why nothing
            was.
        """
        async with self._home_uow() as uow:
            settings = await uow.automation.get(user_id)
            devices: Sequence[Device] = list(await uow.devices.list_all(user_id))
        if settings is None or not settings.enabled:
            return AutomationCycleReport(cycle_skipped=SkipReason.AUTOMATION_DISABLED)

        state = await self._state_store.read(user_id)
        if state.is_automation_suspended(self._clock.now()):
            return AutomationCycleReport(cycle_skipped=SkipReason.MANUAL_CONTROL_ACTIVE)
        if not state.reading.is_usable:
            return AutomationCycleReport(cycle_skipped=SkipReason.NO_SENSOR_DATA)

        demands = self._demands.demands_for(
            settings.temperature_band, settings.humidity_band, state.reading
        )
        performed: list[str] = []
        failed: list[tuple[str, str]] = []
        skipped: list[tuple[str, str]] = []
        for demand in demands:
            result = await self._satisfy(user_id, demand, devices, settings)
            if result is None:
                performed.append(demand.value)
            elif result is SkipReason.NO_SUITABLE_DEVICE:
                skipped.append((demand.value, str(result)))
            else:
                failed.append((demand.value, result))
        return AutomationCycleReport(
            performed=tuple(performed), failed=tuple(failed), skipped=tuple(skipped)
        )

    async def _satisfy(
        self,
        user_id: UserId,
        demand: ClimateDemand,
        devices: Sequence[Device],
        settings: AutomationSettings,
    ) -> SkipReason | str | None:
        """Resolve a demand through the domain selector and perform it.

        Args:
            user_id: Owner of the home.
            demand: Climate demand to satisfy.
            devices: Loaded devices of the home.
            settings: Automation settings used to filter participants.

        Returns:
            None on success, a SkipReason when the domain declines, or a
            failure reason string when the board did not answer.
        """
        target = self._selector.first_supporting(
            devices, demand.capability, settings, automation_only=True
        )
        if target is None:
            return SkipReason.NO_SUITABLE_DEVICE
        try:
            await self._control.apply_to_device(user_id, target.id, demand.capability, manual=False)
        except BoardUnreachableError as error:
            return error.reason
        return None
