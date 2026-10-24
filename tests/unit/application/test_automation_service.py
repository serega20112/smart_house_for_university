"""Tests for the automation cycle (refactoring point 2.6)."""

from __future__ import annotations

from collections.abc import Sequence
from datetime import UTC, datetime
from typing import Never, Self

from tests.conftest import OWNER_UUID, make_device

from backend.application.errors import BoardUnreachableError
from backend.application.interfaces.services.messaging.domain_event_dispatcher import (
    DomainEventDispatcher,
)
from backend.application.interfaces.services.messaging.realtime_publisher import (
    RealtimePublisher,
)
from backend.application.interfaces.services.state.home_state_store import (
    HomeStateStore,
)
from backend.application.interfaces.services.system.clock import Clock
from backend.application.interfaces.unit_of_work.home import HomeUnitOfWorkFactory
from backend.application.services.automation_service import AutomationService
from backend.application.services.device_control import DeviceControlService
from backend.domain.aggregates.automation.automation_settings import AutomationSettings
from backend.domain.aggregates.device.device import Device
from backend.domain.entities.home_state.home_state import HomeState
from backend.domain.identifiers import DeviceId, EspDeviceId, UserId
from backend.domain.policies.climate_policy import DemandCalculator
from backend.domain.policies.device_selector import DeviceSelector
from backend.domain.value_objects.climate.climate_reading import ClimateReading
from backend.domain.value_objects.climate.skip_reason import SkipReason
from backend.domain.value_objects.devices.capability import Capability
from backend.domain.value_objects.devices.device_kind import DeviceKind
from backend.domain.value_objects.devices.relay_channel import RelayChannel

NOW = datetime(2026, 5, 1, 12, 0, tzinfo=UTC)
BOARD = EspDeviceId.generate()


class FakeClock(Clock):
    def now(self) -> datetime:
        return NOW


class JournalingControl(DeviceControlService):
    def __init__(self, journal: list[str], *, accepts: bool = True) -> None:
        self._journal = journal
        self._accepts = accepts
        self.calls: list[tuple[DeviceId, Capability]] = []

    async def apply_to_loaded(
        self,
        user_id: UserId,
        device: Device,
        capability: Capability,
        *,
        manual: bool = True,
    ) -> object:
        self._journal.append("control")
        self.calls.append((device.id, capability))
        if not self._accepts:
            raise BoardUnreachableError("board down")
        return object()


class FakeAutomationRepository:
    def __init__(self, settings: AutomationSettings | None) -> None:
        self._settings = settings

    async def get(self, user_id: UserId) -> AutomationSettings | None:
        return self._settings

    async def save(self, settings: AutomationSettings) -> None:
        pass


class FakeHomeUnitOfWork:
    def __init__(self, settings: AutomationSettings | None, devices: Sequence[Device]) -> None:
        self._settings = settings
        self._devices = devices

    @property
    def devices(self) -> FakeDeviceRepository:
        return FakeDeviceRepository(self._devices)

    @property
    def automation(self) -> FakeAutomationRepository:
        return FakeAutomationRepository(self._settings)

    @property
    def scenarios(self) -> Never:
        raise AssertionError("scenarios must not be touched")

    @property
    def dashboard(self) -> Never:
        raise AssertionError("dashboard must not be touched")

    @property
    def preferences(self) -> Never:
        raise AssertionError("preferences must not be touched")

    async def __aenter__(self) -> Self:
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        del exc_type, exc_val, exc_tb

    async def commit(self) -> None:
        pass

    async def rollback(self) -> None:
        pass


class FakeDeviceRepository:
    def __init__(self, devices: Sequence[Device]) -> None:
        self._devices = devices

    async def list_all(self, user_id: UserId) -> Sequence[Device]:
        return list(self._devices)

    async def get(self, user_id: UserId, device_id: DeviceId) -> Device | None:
        """Отвергает перечитывание: цикл работает с уже прочитанным домом.

        Raises:
            AssertionError: Когда автоматика перечитала выбранное устройство.
        """
        raise AssertionError(f"{device_id} was already read with the rest of the home")

    async def add(self, device: Device) -> None:
        pass

    async def update(self, device: Device) -> None:
        pass

    async def delete(self, user_id: UserId, device_id: DeviceId) -> bool:
        return True


class FakeUnitOfWorkFactory(HomeUnitOfWorkFactory):
    def __init__(self, settings: AutomationSettings | None, devices: Sequence[Device]) -> None:
        self._settings = settings
        self._devices = devices

    def __call__(self) -> FakeHomeUnitOfWork:
        return FakeHomeUnitOfWork(self._settings, self._devices)


class FakeStateStore(HomeStateStore):
    def __init__(self, state: HomeState) -> None:
        self._state = state

    async def read(self, user_id: UserId) -> HomeState:
        return self._state

    async def record_background_reading(
        self,
        user_id: UserId,
        board_id: EspDeviceId,
        reading: ClimateReading,
        changed_at: datetime,
    ) -> ClimateReading:
        return ClimateReading()

    async def record_relay_report(
        self,
        user_id: UserId,
        board_id: EspDeviceId,
        states: Sequence[bool],
        changed_at: datetime,
    ) -> tuple[int, ...]:
        return ()

    async def record_board_online(
        self, user_id: UserId, board_id: EspDeviceId, online: bool, changed_at: datetime
    ) -> bool:
        return self._state.is_board_online(board_id)

    async def record_command_result(
        self,
        user_id: UserId,
        board_id: EspDeviceId,
        device_id: DeviceId,
        channel: int,
        status: object,
        changed_at: datetime,
    ) -> None:
        pass

    async def forget_device_status(self, user_id: UserId, device_id: DeviceId) -> None:
        pass

    async def set_override_until(self, user_id: UserId, until: datetime | None) -> None:
        pass

    async def claim_summary_slot(self, user_id: UserId, key: str, window_sec: int) -> bool:
        return True


class StubRealtime(RealtimePublisher):
    async def publish(self, user_id: UserId, event: str, payload: dict) -> None:
        pass

    async def broadcast(self, event: str, payload: dict) -> None:
        pass


class StubDispatcher(DomainEventDispatcher):
    async def dispatch(self, events: Sequence[object]) -> None:
        pass


def _make_service(
    settings: AutomationSettings | None,
    devices: list[Device],
    state: HomeState | None = None,
    *,
    accepts: bool = True,
) -> tuple[AutomationService, JournalingControl]:
    journal: list[str] = []
    control = JournalingControl(journal, accepts=accepts)
    if state is None:
        state = _home_state()
    service = AutomationService(
        home_uow=FakeUnitOfWorkFactory(settings, devices),
        control=control,
        state_store=FakeStateStore(state),
        demands=DemandCalculator(),
        selector=DeviceSelector(),
        clock=FakeClock(),
    )
    return service, control


def _home_state() -> HomeState:
    """Builds a home whose only board answers.

    Returns:
        HomeState: State of a home with one reachable board.
    """
    return HomeState(user_id=UserId.parse(OWNER_UUID), online_boards=frozenset({BOARD}))


def _cold_reading() -> ClimateReading:
    from backend.domain.value_objects.climate.temperature import Temperature

    return ClimateReading(temperature=Temperature(15.0), humidity=None)


def _enabled_settings() -> AutomationSettings:
    settings = AutomationSettings.create(UserId.parse(OWNER_UUID))
    settings._set_enabled(True)
    return settings


async def test_run_cycle_skips_when_automation_disabled() -> None:
    settings = _enabled_settings()
    settings._set_enabled(False)
    service, control = _make_service(settings, [])
    report = await service.run_cycle(UserId.parse(OWNER_UUID))
    assert report.cycle_skipped is SkipReason.AUTOMATION_DISABLED
    assert report.performed == ()
    assert control.calls == []


async def test_run_cycle_skips_when_manual_control_active() -> None:
    settings = _enabled_settings()
    state = _home_state()
    state.suspend_automation_for(NOW, 5)
    service, control = _make_service(settings, [make_device()], state=state)
    report = await service.run_cycle(UserId.parse(OWNER_UUID))
    assert report.cycle_skipped is SkipReason.MANUAL_CONTROL_ACTIVE
    assert control.calls == []


async def test_run_cycle_skips_when_no_sensor_data() -> None:
    settings = _enabled_settings()
    service, control = _make_service(settings, [make_device()])
    report = await service.run_cycle(UserId.parse(OWNER_UUID))
    assert report.cycle_skipped is SkipReason.NO_SENSOR_DATA
    assert control.calls == []


async def test_run_cycle_board_failure_does_not_stop_other_demands() -> None:
    from backend.domain.value_objects.climate.temperature import Temperature

    settings = _enabled_settings()
    settings.aim_at_temperature(Temperature(22.0))
    heater1 = make_device(
        name="Heater 1",
        kind=DeviceKind.HEATER,
        capabilities=frozenset({Capability.HEAT, Capability.OFF}),
        channel=RelayChannel(1),
    )
    heater2 = make_device(
        name="Heater 2",
        kind=DeviceKind.HEATER,
        capabilities=frozenset({Capability.HEAT, Capability.OFF}),
        channel=RelayChannel(2),
    )
    hot_state = _home_state()
    hot_state.apply_reading(BOARD, _cold_reading(), NOW)
    service, control = _make_service(settings, [heater1, heater2], state=hot_state, accepts=False)
    report = await service.run_cycle(UserId.parse(OWNER_UUID))
    assert len(control.calls) == 1
    assert report.performed == ()
    assert len(report.failed) == 1
    assert "board down" in report.failed[0][1]


async def test_run_cycle_reports_skipped_when_no_device_supports_demand() -> None:
    from backend.domain.value_objects.climate.temperature import Temperature

    settings = _enabled_settings()
    settings.aim_at_temperature(Temperature(22.0))
    hot_state = _home_state()
    hot_state.apply_reading(BOARD, _cold_reading(), NOW)
    service, control = _make_service(settings, [], state=hot_state)
    report = await service.run_cycle(UserId.parse(OWNER_UUID))
    assert len(report.skipped) == 1
    assert report.skipped[0][1] == SkipReason.NO_SUITABLE_DEVICE.value
    assert control.calls == []


async def test_run_cycle_reports_performed_on_success() -> None:
    from backend.domain.value_objects.climate.temperature import Temperature

    settings = _enabled_settings()
    settings.aim_at_temperature(Temperature(22.0))
    heater = make_device(
        name="Heater",
        kind=DeviceKind.HEATER,
        capabilities=frozenset({Capability.HEAT, Capability.OFF}),
        channel=RelayChannel(1),
    )
    hot_state = _home_state()
    hot_state.apply_reading(BOARD, _cold_reading(), NOW)
    service, control = _make_service(settings, [heater], state=hot_state)
    report = await service.run_cycle(UserId.parse(OWNER_UUID))
    assert len(report.performed) == 1
    assert report.performed[0] == "HEAT"
    assert len(control.calls) == 1
