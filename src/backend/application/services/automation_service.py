"""Держит климат внутри коридора, который настроил человек.

Один цикл читает нынешние значения, спрашивает модель, какие требования они порождают,
находит на каждое требование устройство и выполняет его. Цикл идёт для одного дома за
раз, поэтому каждый аккаунт остаётся независимым, хотя один процесс обслуживает всех.

Сервис никогда не держит транзакцию на весь цикл: конфигурацию читают один раз, после
чего каждая команда идёт в железо, не удерживая соединение с базой.
"""

from __future__ import annotations

from collections.abc import Sequence

from backend.application.errors import BoardUnreachableError
from backend.application.interfaces.services.state.home_state_store import HomeStateStore
from backend.application.interfaces.services.system.clock import Clock
from backend.application.interfaces.unit_of_work.home import HomeUnitOfWorkFactory
from backend.application.services.device_control import DeviceControlService
from backend.domain.aggregates.automation.automation_settings import AutomationSettings
from backend.domain.aggregates.device.device import Device
from backend.domain.identifiers import UserId
from backend.domain.policies.climate_policy import ClimateDemand, DemandCalculator
from backend.domain.policies.device_selector import DeviceSelector
from backend.domain.value_objects.automation.automation_cycle_report import AutomationCycleReport
from backend.domain.value_objects.climate.skip_reason import SkipReason


class AutomationService:
    """Проводит один цикл автоматизации одного дома."""

    def __init__(
        self,
        home_uow: HomeUnitOfWorkFactory,
        control: DeviceControlService,
        state_store: HomeStateStore,
        demands: DemandCalculator,
        selector: DeviceSelector,
        clock: Clock,
    ) -> None:
        """Инициализирует сервис.

        Args:
            home_uow: Фабрика транзакций над конфигурацией.
            control: Сервис, выполняющий способности на железе.
            state_store: Надёжный дом изменчивого состояния.
            demands: Часть модели, решающая, о чём просит климат.
            selector: Доменный поиск устройств по способности.
            clock: Источник текущего времени.
        """
        self._home_uow = home_uow
        self._control = control
        self._state_store = state_store
        self._demands = demands
        self._selector = selector
        self._clock = clock

    async def run_cycle(self, user_id: UserId) -> AutomationCycleReport:
        """Проводит один цикл и отчитывается, что он сделал.

        Args:
            user_id: Владелец дома, который автоматизируют.

        Returns:
            AutomationCycleReport: Выполненные требования или почему не было ни одного.
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
        """Разрешает требование через доменный поиск и выполняет его.

        Args:
            user_id: Владелец дома.
            demand: Требование климата, которое надо удовлетворить.
            devices: Загруженные устройства дома.
            settings: Настройка автоматизации для отсева участников.

        Returns:
            None при успехе, SkipReason, когда модель отказывает, или строка причины
            отказа, когда плата не ответила.
        """
        target = self._selector.first_supporting(
            devices, demand.capability, settings, automation_only=True
        )
        if target is None:
            return SkipReason.NO_SUITABLE_DEVICE
        try:
            await self._control.apply_to_loaded(user_id, target, demand.capability, manual=False)
        except BoardUnreachableError as error:
            return error.reason
        return None
