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

from backend.application.dto.automation import AutomationCycleReport
from backend.application.ports.services import Clock, HomeStateStore
from backend.application.ports.unit_of_work.home import HomeUnitOfWorkFactory
from backend.application.services.device_control import DeviceControlService
from backend.domain.climate.automation_settings import AutomationSettings
from backend.domain.climate.climate_demand import ClimateDemand, DemandCalculator
from backend.domain.devices.device import Device
from backend.domain.identifiers import UserId

AUTOMATION_DISABLED = "automation_disabled"
MANUAL_CONTROL_WINS = "manual_control_active"
NO_MEASUREMENT = "no_sensor_data"


class AutomationService:
    """Runs one automation cycle of a home."""

    def __init__(
        self,
        home_uow: HomeUnitOfWorkFactory,
        control: DeviceControlService,
        state_store: HomeStateStore,
        demands: DemandCalculator,
        clock: Clock,
    ) -> None:
        """Initialize the service.

        Args:
            home_uow: Factory producing transactions over the configuration.
            control: Service performing capabilities against the hardware.
            state_store: Durable home of the volatile state.
            demands: Model component deciding what the climate is asking for.
            clock: Source of the current time.

        Returns:
            None.
        """
        self._home_uow = home_uow
        self._control = control
        self._state_store = state_store
        self._demands = demands
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
            devices = list(await uow.devices.list_all(user_id))
        if settings is None or not settings.enabled:
            return AutomationCycleReport(skipped_reason=AUTOMATION_DISABLED)

        state = await self._state_store.load(user_id)
        if state.is_automation_suspended(self._clock.now()):
            return AutomationCycleReport(skipped_reason=MANUAL_CONTROL_WINS)
        if not state.reading.is_usable:
            return AutomationCycleReport(skipped_reason=NO_MEASUREMENT)

        performed: list[str] = []
        for demand in self._demands.demands_for(
            settings.temperature_band, settings.humidity_band, state.reading
        ):
            if await self._satisfy(user_id, demand, devices, settings):
                performed.append(demand.value)
        return AutomationCycleReport(performed=tuple(performed))

    async def _satisfy(
        self,
        user_id: UserId,
        demand: ClimateDemand,
        devices: Sequence[Device],
        settings: AutomationSettings,
    ) -> bool:
        target = _first_automation_device(devices, demand, settings)
        if target is None:
            return False
        await self._control.apply_to_device(user_id, target.id, demand.capability, manual=False)
        return True


def _first_automation_device(
    devices: Sequence[Device], demand: ClimateDemand, settings: AutomationSettings
) -> Device | None:
    for device in devices:
        if not device.takes_part_in_automation:
            continue
        if not settings.device_participates(device.id):
            continue
        if device.supports(demand.capability):
            return device
    return None
