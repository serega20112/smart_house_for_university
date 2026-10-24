from __future__ import annotations

from collections.abc import Sequence
from datetime import UTC, datetime
from typing import Never, Self

import pytest
from tests.conftest import OWNER_UUID, make_device

from backend.application.dto.boards.board_command_result import BoardCommandResult
from backend.application.errors import (
    BoardNotChosenError,
    BoardUnreachableError,
    DeviceNotFoundError,
)
from backend.application.interfaces.services.boards.board_gateway import (
    BoardGateway,
)
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
from backend.application.services.device_control import DeviceControlService
from backend.domain.aggregates.device.device import Device
from backend.domain.aggregates.esp_device.esp_device import EspDevice
from backend.domain.entities.home_state.home_state import HomeState
from backend.domain.identifiers import DeviceId, EspDeviceId, UserId
from backend.domain.policies.device_selector import DeviceSelector
from backend.domain.value_objects.boards.network_profile import NetworkProfile
from backend.domain.value_objects.boards.pairing_key import PairingKey
from backend.domain.value_objects.climate.climate_reading import ClimateReading
from backend.domain.value_objects.devices.capability import Capability
from backend.domain.value_objects.devices.device_status import DeviceStatus

NOW = datetime(2026, 5, 1, 12, 0, tzinfo=UTC)


class FakeClock(Clock):
    def now(self) -> datetime:
        return NOW


class FakeBoardGateway(BoardGateway):
    def __init__(self, journal: list[str], accepts: bool = True) -> None:
        self._journal = journal
        self._accepts = accepts
        self.commands: list[tuple[int, bool]] = []
        self.refuse_channels: set[int] = set()
        self.board_id = EspDeviceId.generate()

    async def board_for(self, user_id: UserId) -> EspDeviceId | None:
        del user_id
        return self.board_id

    async def set_relay(
        self, user_id: UserId, board_id: DeviceId, channel: int, energized: bool
    ) -> BoardCommandResult:
        self.commands.append((channel, energized))
        self._journal.append("board")
        if channel in self.refuse_channels:
            return BoardCommandResult(accepted=False, reason="no_answer")
        return BoardCommandResult(accepted=self._accepts, reason=None if self._accepts else "gone")

    async def request_state(self, user_id: UserId, board_id: DeviceId) -> None:
        pass

    async def set_network(
        self, user_id: UserId, board_id: DeviceId, profile: NetworkProfile
    ) -> BoardCommandResult:
        return BoardCommandResult(accepted=True)

    async def is_connected(self, user_id: UserId, board_id: DeviceId) -> bool:
        return True


class FakeDeviceRepository:
    def __init__(self) -> None:
        self.devices: list[Device] = []

    async def list_all(self, user_id: UserId) -> Sequence[Device]:
        return list(self.devices)

    async def get(self, user_id: UserId, device_id: DeviceId) -> Device | None:
        return next((device for device in self.devices if device.id == device_id), None)

    async def add(self, device: Device) -> None:
        self.devices.append(device)

    async def update(self, device: Device) -> None:
        """Отвергает запись: команда реле строку конфигурации не меняет.

        Args:
            device: Агрегат, который сервис попытался сохранить.

        Raises:
            AssertionError: Когда после команды появилась запись конфигурации.
        """
        raise AssertionError(f"{device.id} must not be rewritten after a relay command")

    async def delete(self, user_id: UserId, device_id: DeviceId) -> bool:
        return True


class FakeBoardRepository:
    """Платы дома, известные хранилищу конфигурации."""

    def __init__(self) -> None:
        self.boards: list[EspDevice] = []

    async def list_all(self, user_id: UserId) -> Sequence[EspDevice]:
        """Возвращает все платы аккаунта.

        Args:
            user_id: Владелец плат.

        Returns:
            Sequence[EspDevice]: Платы, которые хранилище помнит.
        """
        return list(self.boards)


class FakeRepository:
    """A repository path that is never used by the service under test."""

    def __getattribute__(self, name: str) -> Never:
        raise AssertionError(f"{name} must not be touched by the device control service")


class RecordingHomeUnitOfWork:
    def __init__(
        self, devices: FakeDeviceRepository, boards: FakeBoardRepository, journal: list[str]
    ) -> None:
        self._devices = devices
        self._boards = boards
        self._journal = journal
        self.is_open = False

    @property
    def devices(self) -> FakeDeviceRepository:
        return self._devices

    @property
    def boards(self) -> FakeBoardRepository:
        return self._boards

    @property
    def automation(self) -> FakeRepository:
        return FakeRepository()

    @property
    def scenarios(self) -> FakeRepository:
        return FakeRepository()

    @property
    def dashboard(self) -> FakeRepository:
        return FakeRepository()

    @property
    def preferences(self) -> FakeRepository:
        return FakeRepository()

    async def __aenter__(self) -> Self:
        self.is_open = True
        self._journal.append("uow_open")
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        self.is_open = False
        if exc_type is not None:
            self._journal.append("uow_rollback")

    async def commit(self) -> None:
        self._journal.append("uow_commit")

    async def rollback(self) -> None:
        self._journal.append("uow_rollback")


class FakeHomeUnitOfWorkFactory(HomeUnitOfWorkFactory):
    def __init__(self, devices: FakeDeviceRepository, journal: list[str]) -> None:
        self._devices = devices
        self._journal = journal
        self.boards = FakeBoardRepository()
        self.units: list[RecordingHomeUnitOfWork] = []

    def __call__(self) -> RecordingHomeUnitOfWork:
        unit = RecordingHomeUnitOfWork(self._devices, self.boards, self._journal)
        self.units.append(unit)
        return unit


class FakeStateStore(HomeStateStore):
    def __init__(self, journal: list[str]) -> None:
        self._journal = journal
        self.state = HomeState(user_id=UserId.parse(OWNER_UUID))
        self.recorded_commands: list[tuple[DeviceId, DeviceStatus]] = []

    async def read(self, user_id: UserId) -> HomeState:
        self._journal.append("state_read")
        return self.state

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
        return self.state.is_board_online(board_id)

    async def record_command_result(
        self,
        user_id: UserId,
        board_id: EspDeviceId,
        device_id: DeviceId,
        channel: int,
        status: DeviceStatus,
        changed_at: datetime,
    ) -> None:
        self._journal.append("state_record_command")
        self.recorded_commands.append((device_id, status))
        self.state.apply_command(board_id, device_id, channel, status, changed_at)

    async def forget_device_status(self, user_id: UserId, device_id: DeviceId) -> None:
        pass

    async def set_override_until(self, user_id: UserId, until: datetime | None) -> None:
        pass

    async def claim_summary_slot(self, user_id: UserId, key: str, window_sec: int) -> bool:
        return True


class FakeRealtimePublisher(RealtimePublisher):
    def __init__(self, journal: list[str]) -> None:
        self._journal = journal
        self.published: list[tuple[UserId, str]] = []

    async def publish(self, user_id: UserId, event: str, payload: dict) -> None:
        self._journal.append("publish")
        self.published.append((user_id, event))

    async def broadcast(self, event: str, payload: dict) -> None:
        pass


class FakeDispatcher(DomainEventDispatcher):
    def __init__(self, journal: list[str]) -> None:
        self._journal = journal
        self.dispatched: list[object] = []

    async def dispatch(self, events: Sequence[object]) -> None:
        self._journal.extend("dispatch" for _ in events)
        self.dispatched.extend(events)


def make_service(
    journal: list[str], accepts: bool = True
) -> tuple[DeviceControlService, FakeDeviceRepository, FakeBoardGateway, FakeStateStore]:
    devices = FakeDeviceRepository()
    boards = FakeBoardGateway(journal, accepts)
    state = FakeStateStore(journal)
    realtime = FakeRealtimePublisher(journal)
    dispatcher = FakeDispatcher(journal)
    service = DeviceControlService(
        home_uow=FakeHomeUnitOfWorkFactory(devices, journal),
        boards=boards,
        state_store=state,
        realtime=realtime,
        dispatcher=dispatcher,
        clock=FakeClock(),
        selector=DeviceSelector(),
    )
    return service, devices, boards, state


def make_service_over(
    factory: FakeHomeUnitOfWorkFactory, boards: FakeBoardGateway, journal: list[str]
) -> DeviceControlService:
    """Собирает сервис над подделками, которые тесту важно видеть.

    Args:
        factory: Фабрика транзакций с доступными тесту хранилищами.
        boards: Шлюз к железу, записывающий команды.
        journal: Журнал порядка шагов.

    Returns:
        DeviceControlService: Сервис над этими подделками.
    """
    return DeviceControlService(
        home_uow=factory,
        boards=boards,
        state_store=FakeStateStore(journal),
        realtime=FakeRealtimePublisher(journal),
        dispatcher=FakeDispatcher(journal),
        clock=FakeClock(),
        selector=DeviceSelector(),
    )


def pair_boards(user_id: UserId, count: int) -> list[EspDevice]:
    """Строит несколько сопряжённых плат одного аккаунта.

    Args:
        user_id: Владелец плат.
        count: Сколько плат нужно.

    Returns:
        list[EspDevice]: Платы с разными ключами.
    """
    return [
        EspDevice.pair(user_id, f"Board {number}", PairingKey.generate(), NOW)
        for number in range(1, count + 1)
    ]


async def test_apply_to_device_records_confirmation_before_publishing_and_dispatching() -> None:
    journal: list[str] = []
    service, devices, _boards, _state = make_service(journal)
    device = make_device()
    devices.devices.append(device)

    view = await service.apply_to_device(device.user_id, device.id, Capability.ON)

    assert view.status.value == "ACTIVE"
    assert journal == [
        "uow_open",
        "uow_open",
        "board",
        "state_record_command",
        "publish",
        "dispatch",
    ]


async def test_apply_to_device_asks_the_board_outside_a_transaction() -> None:
    journal: list[str] = []
    _, devices, _boards, _state = make_service(journal)
    device = make_device()
    devices.devices.append(device)
    factory = FakeHomeUnitOfWorkFactory(devices, journal)
    openness: list[bool] = []
    boards = FakeBoardGateway(journal)
    original_set_relay = boards.set_relay

    async def set_relay(
        user_id: UserId, board_id: DeviceId, channel: int, energized: bool
    ) -> BoardCommandResult:
        openness.extend(unit.is_open for unit in factory.units)
        return await original_set_relay(user_id, board_id, channel, energized)

    boards.set_relay = set_relay
    service = DeviceControlService(
        home_uow=factory,
        boards=boards,
        state_store=FakeStateStore(journal),
        realtime=FakeRealtimePublisher(journal),
        dispatcher=FakeDispatcher(journal),
        clock=FakeClock(),
        selector=DeviceSelector(),
    )

    await service.apply_to_device(device.user_id, device.id, Capability.ON)

    assert journal.count("board") == 1
    assert not any(openness)


async def test_apply_to_device_refused_leaves_everything_untouched() -> None:
    journal: list[str] = []
    service, devices, _boards, state = make_service(journal, accepts=False)
    device = make_device()

    devices.devices.append(device)
    with pytest.raises(BoardUnreachableError):
        await service.apply_to_device(device.user_id, device.id, Capability.ON)

    assert not state.recorded_commands
    assert "publish" not in journal
    assert "dispatch" not in journal
    assert device.pull_events() == ()


async def test_apply_to_device_unknown_device_raises_without_a_board_call() -> None:
    journal: list[str] = []
    service, _devices, boards, _state = make_service(journal)

    with pytest.raises(DeviceNotFoundError):
        await service.apply_to_device(UserId.parse(OWNER_UUID), DeviceId.generate(), Capability.ON)

    assert boards.commands == []


async def test_apply_to_all_keeps_going_when_one_board_refuses() -> None:
    journal: list[str] = []
    service, devices, boards, state = make_service(journal)
    lamp = make_device(name="Lamp")
    heater = make_device(name="Heater", channel=4)
    devices.devices.extend([lamp, heater])
    boards.refuse_channels.add(4)

    report = await service.apply_to_all(lamp.user_id, [lamp, heater], Capability.ON)

    assert [view.name for view in report.devices] == ["Lamp"]
    assert [(failure.name, failure.reason) for failure in report.failed] == [
        ("Heater", "no_answer")
    ]
    assert [device_id for device_id, _status in state.recorded_commands] == [lamp.id]
    assert "publish" in journal


async def test_apply_to_all_reports_a_fully_refused_home_as_data() -> None:
    journal: list[str] = []
    service, devices, boards, state = make_service(journal)
    lamp = make_device(name="Lamp")
    devices.devices.append(lamp)
    boards.refuse_channels.add(1)

    report = await service.apply_to_all(lamp.user_id, [lamp], Capability.ON)

    assert report.devices == ()
    assert [failure.name for failure in report.failed] == ["Lamp"]
    assert not state.recorded_commands
    assert "publish" not in journal


async def test_unbound_device_in_a_two_board_home_asks_for_a_choice() -> None:
    """Устройство без платы в доме с двумя платами не угадывает адресата.

    Returns:
        None: Только проверка отказа без единой команды на реле.
    """
    journal: list[str] = []
    devices = FakeDeviceRepository()
    factory = FakeHomeUnitOfWorkFactory(devices, journal)
    boards = FakeBoardGateway(journal)
    service = make_service_over(factory, boards, journal)
    device = make_device()
    devices.devices.append(device)
    factory.boards.boards.extend(pair_boards(device.user_id, 2))

    with pytest.raises(BoardNotChosenError):
        await service.apply_to_device(device.user_id, device.id, Capability.ON)

    assert boards.commands == []
    assert "publish" not in journal


async def test_apply_to_all_reports_an_unbound_device_as_a_failure() -> None:
    """Непривязанное устройство попадает в отчёт, а остальные всё равно работают.

    Returns:
        None: Только проверка отчёта по двум устройствам.
    """
    journal: list[str] = []
    devices = FakeDeviceRepository()
    factory = FakeHomeUnitOfWorkFactory(devices, journal)
    boards = FakeBoardGateway(journal)
    service = make_service_over(factory, boards, journal)
    bound = make_device(name="Lamp", board_id=EspDeviceId.generate())
    unbound = make_device(name="Heater", channel=4)
    devices.devices.extend([bound, unbound])
    factory.boards.boards.extend(pair_boards(bound.user_id, 2))

    report = await service.apply_to_all(bound.user_id, [bound, unbound], Capability.ON)

    assert [view.name for view in report.devices] == ["Lamp"]
    assert [(failure.name, failure.reason) for failure in report.failed] == [
        ("Heater", "board_not_chosen")
    ]
