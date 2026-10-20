"""Scenarios fail alone and start only after the board confirmed.

The service advances every scenario of a home in one tick. The rules under test
are the ones the ТЗ asks for: an expected refusal throws only its scenario into
FAILED, the tick carries on with the rest, and the commands are performed before
the aggregate is recorded as running, so a refusal never leaves a scenario
claiming to act.
"""

from datetime import UTC, datetime

from tests.conftest import OWNER_UUID, make_device

from smart_home.application.ports.boards import BoardCommandResult, BoardGateway
from smart_home.application.ports.events import (
    DomainEventDispatcher,
    Notification,
    NotificationFactory,
    RealtimePublisher,
    UserNotifier,
)
from smart_home.application.ports.services import Clock, HomeStateStore
from smart_home.application.ports.unit_of_work.home import HomeUnitOfWork
from smart_home.application.services.device_control import DeviceControlService
from smart_home.application.services.scenario_service import ScenarioService
from smart_home.domain.climate.climate_reading import ClimateReading
from smart_home.domain.climate.home_state import HomeState
from smart_home.domain.devices.capability import Capability
from smart_home.domain.devices.device import Device
from smart_home.domain.devices.device_status import DeviceStatus
from smart_home.domain.identifiers import DeviceId, UserId
from smart_home.domain.scenarios.completion_behavior import CompletionBehavior
from smart_home.domain.scenarios.scenario import Scenario
from smart_home.domain.scenarios.scenario_action import ScenarioAction
from smart_home.domain.scenarios.scenario_status import ScenarioStatus
from smart_home.domain.services.device_selector import DeviceSelector

NOW = datetime(2027, 6, 1, 12, 0, tzinfo=UTC)


class FixedClock(Clock):
    """Answers every question about the moment with the same answer."""

    def now(self) -> datetime:
        """Return the fixed moment of this session.

        Returns:
            datetime: The moment every clock call carries now.
        """
        return NOW


class SelectiveBoardGateway(BoardGateway):
    """Accepts every command but the ones of the boards it refuses.

    Args:
        refused: Boards that pull the plug.

    Returns:
        None.
    """

    def __init__(self, refused: set[DeviceId]) -> None:
        self._refused = refused
        self.driven: list[DeviceId] = []

    async def set_relay(
        self, user_id: UserId, board_id: DeviceId, channel: int, energized: bool
    ) -> BoardCommandResult:
        """Drive a relay, refusing the ones on the unreachable boards.

        Args:
            user_id: Owner of the board.
            board_id: Board the device is wired to.
            channel: Channel the relay holds.
            energized: Direction the contact is asked to take.

        Returns:
            BoardCommandResult: What the board answered.
        """
        del user_id, channel, energized
        if board_id in self._refused:
            return BoardCommandResult(accepted=False, reason="offline")
        self.driven.append(board_id)
        return BoardCommandResult(accepted=True)

    async def request_state(self, user_id: UserId, board_id: DeviceId) -> None:
        """Do nothing.

        Args:
            user_id: Owner of the board.
            board_id: Board asked to resend its state.

        Returns:
            None.
        """
        del user_id, board_id

    async def set_network(
        self, user_id: UserId, board_id: DeviceId, profile: object
    ) -> BoardCommandResult:
        """Do nothing beyond confirming.

        Args:
            user_id: Owner of the board.
            board_id: Board to reprogram.
            profile: Network the board would be given.

        Returns:
            BoardCommandResult: Accepted, as nothing else happens here.
        """
        del user_id, board_id, profile
        return BoardCommandResult(accepted=True)

    def is_connected(self, user_id: UserId, board_id: DeviceId) -> bool:
        """Report every board reachable.

        Args:
            user_id: Owner of the board.
            board_id: Board in question.

        Returns:
            bool: True, the refusal is decided by the accept result.
        """
        del user_id, board_id
        return True


class StubStateStore(HomeStateStore):
    """Reads the one state every test starts from.

    Args:
        state: The state the readers see.

    Returns:
        None.
    """

    def __init__(self, state: HomeState) -> None:
        self.state = state

    async def read(self, user_id: UserId) -> HomeState:
        """Return the state of the home.

        Args:
            user_id: Owner of the home.

        Returns:
            HomeState: The state every reader shares.
        """
        del user_id
        return self.state

    async def record_background_reading(
        self, user_id: UserId, reading: ClimateReading, changed_at: datetime
    ) -> ClimateReading:
        """Register a reading the boards reported.

        Args:
            user_id: Owner of the home.
            reading: Measured values.
            changed_at: Moment of the report.

        Returns:
            ClimateReading: Nothing has moved behind this stub's back.
        """
        del user_id, changed_at
        return ClimateReading()

    async def record_relay_report(
        self, user_id: UserId, states: list[bool], changed_at: datetime
    ) -> tuple[int, ...]:
        """Register the positions a board reported.

        Args:
            user_id: Owner of the board.
            states: Contact positions.
            changed_at: Moment of the report.

        Returns:
            tuple[int, ...]: Nothing has moved behind this stub's back.
        """
        del user_id, states, changed_at
        return ()

    async def record_board_online(
        self, user_id: UserId, online: bool, changed_at: datetime
    ) -> bool:
        """Record reachability of the board.

        Args:
            user_id: Owner of the board.
            online: Whether the board answers.
            changed_at: Moment of the transition.

        Returns:
            bool: The flag the state carried before.
        """
        del changed_at
        was = self.state.board_online
        if not online:
            self.state.board_online = False
            self.state.device_modes.clear()
        return was

    async def record_command_result(
        self, user_id: UserId, device: Device, status: DeviceStatus, changed_at: datetime
    ) -> None:
        """Record what the board confirmed.

        Args:
            user_id: Owner of the device.
            device: Device that was driven.
            status: State the device reached.
            changed_at: Moment of the confirmation.

        Returns:
            None.
        """
        del user_id
        self.state.apply_command(device, status, changed_at)

    async def forget_device_status(self, user_id: UserId, device_id: DeviceId) -> None:
        """Drop one device from the memory.

        Args:
            user_id: Owner of the device.
            device_id: Device that stopped existing.

        Returns:
            None.
        """
        del user_id
        self.state.forget_device(device_id)

    async def set_override_until(self, user_id: UserId, until: object) -> None:
        """Accept the override window.

        Args:
            user_id: Owner of the home.
            until: Moment the window closes.

        Returns:
            None.
        """
        del user_id, until

    async def claim_summary_slot(self, user_id: object, key: object, window_sec: object) -> bool:
        """Hand out the right to send.

        Args:
            user_id: Owner of the home.
            key: Name of the throttle.
            window_sec: Length of the window.

        Returns:
            bool: Always True, there is nothing to throttle here.
        """
        del user_id, key, window_sec
        return True


class ScenarioRepository:
    """In memory home of the scenarios of the test."""

    def __init__(self, scenarios: list[Scenario]) -> None:
        self.scenarios = scenarios
        self.updates: list[Scenario] = []

    async def list_all(self, user_id: UserId) -> list[Scenario]:
        """Return the scenarios of an account.

        Args:
            user_id: Owner the scenarios belong to.

        Returns:
            list[Scenario]: Scenarios, newest first.
        """
        del user_id
        return list(reversed(self.scenarios))

    async def list_holding_priority(self, user_id: UserId) -> list[Scenario]:
        """Return the scenarios still holding priority.

        Args:
            user_id: Owner the scenarios belong to.

        Returns:
            list[Scenario]: Pending and running scenarios.
        """
        del user_id
        return [scenario for scenario in self.scenarios if scenario.status.holds_control_priority]

    async def get(self, user_id: UserId, scenario_id: object) -> Scenario | None:
        """Return one scenario.

        Args:
            user_id: Owner of the scenario.
            scenario_id: Identifier of the scenario.

        Returns:
            Scenario | None: The scenario, or None.
        """
        del user_id
        return next((s for s in self.scenarios if s.id == scenario_id), None)

    async def add(self, scenario: Scenario) -> None:
        """Store one scenario.

        Args:
            scenario: Scenario to hold.

        Returns:
            None.
        """
        self.scenarios.append(scenario)

    async def update(self, scenario: Scenario) -> None:
        """Record the fact that a scenario was written back.

        Args:
            scenario: Scenario with a changed stage.

        Returns:
            None.
        """
        self.updates.append(scenario)


class DeviceRepository:
    """In memory home of the devices of the test."""

    def __init__(self, devices: list[Device]) -> None:
        self.devices = devices

    async def list_all(self, user_id: UserId) -> list[Device]:
        """Return the devices of an account.

        Args:
            user_id: Owner the devices belong to.

        Returns:
            list[Device]: The devices the test gave.
        """
        del user_id
        return list(self.devices)

    async def get(self, user_id: UserId, device_id: object) -> Device | None:
        """Return one device.

        Args:
            user_id: Owner of the device.
            device_id: Identifier of the device.

        Returns:
            Device | None: The device, or None.
        """
        del user_id
        return next((d for d in self.devices if d.id == device_id), None)

    async def add(self, device: Device) -> None:
        """Store one device.

        Args:
            device: Device to hold.

        Returns:
            None.
        """
        self.devices.append(device)

    async def update(self, device: Device) -> None:
        """Accept the write of one device.

        Args:
            device: Device with changed configuration.

        Returns:
            None.
        """
        self.devices = [
            device if existing.id == device.id else existing for existing in self.devices
        ]

    async def delete(self, user_id: UserId, device_id: object) -> bool:
        """Refuse to remove anything.

        Args:
            user_id: Owner of the device.
            device_id: Device about to be removed.

        Returns:
            bool: False, nothing was removed.
        """
        del user_id, device_id
        return False


class FakeUow(HomeUnitOfWork):
    """A transaction whose only job is to hand out the repositories.

    Args:
        devices: Repository of the devices.
        scenarios: Repository of the scenarios.

    Returns:
        None.
    """

    def __init__(self, devices: DeviceRepository, scenarios: ScenarioRepository) -> None:
        self._devices = devices
        self._scenarios = scenarios
        self.commits = 0

    @property
    def devices(self) -> DeviceRepository:
        """Return the repository of the devices.

        Returns:
            DeviceRepository: The in memory stall.
        """
        return self._devices

    @property
    def automation(self) -> object:
        """The automation repository is never used by the scenarios.

        Raises:
            NotImplementedError: Always, as the tickets do not read it.
        """
        raise NotImplementedError

    @property
    def scenarios(self) -> ScenarioRepository:
        """Return the repository of the scenarios.

        Returns:
            ScenarioRepository: The in memory stall.
        """
        return self._scenarios

    @property
    def dashboard(self) -> object:
        """The dashboard repository is never used by the scenarios.

        Raises:
            NotImplementedError: Always, as the tickets do not read it.
        """
        raise NotImplementedError

    @property
    def preferences(self) -> object:
        """The preferences repository is never used by the scenarios.

        Raises:
            NotImplementedError: Always, as the tickets do not read it.
        """
        raise NotImplementedError

    async def commit(self) -> None:
        """Confirm the block.

        Returns:
            None.
        """
        self.commits += 1

    async def rollback(self) -> None:
        """Undo the block.

        Returns:
            None.
        """


class FakeFactory:
    """Hands each call of the service the same transaction.

    Args:
        uow: Transaction the service is given.

    Returns:
        None.
    """

    def __init__(self, uow: FakeUow) -> None:
        self._uow = uow
        self.opened = 0

    def __call__(self) -> FakeUow:
        """Produce the transaction once more.

        Returns:
            FakeUow: The shared transaction.
        """
        self.opened += 1
        return self._uow


class RecordingRealtime(RealtimePublisher):
    """Records the events published to the clients.

    Args:
        None.

    Returns:
        None.
    """

    def __init__(self) -> None:
        self.published: list[str] = []

    async def publish(self, user_id: object, event: str, payload: object) -> None:
        """Record one event.

        Args:
            user_id: Recipient of the event.
            event: Name of the event.
            payload: Content of the event.

        Returns:
            None.
        """
        del user_id, payload
        self.published.append(event)

    async def broadcast(self, event: object, payload: object) -> None:
        """Do nothing.

        Args:
            event: Name of the event.
            payload: Content of the event.

        Returns:
            None.
        """
        del event, payload


class RecordingDispatcher(DomainEventDispatcher):
    """Records the facts handed to the reactions.

    Args:
        None.

    Returns:
        None.
    """

    def __init__(self) -> None:
        self.dispatched: list[object] = []

    async def dispatch(self, events: object) -> None:
        """Record one batch of facts.

        Args:
            events: Facts of an aggregate.

        Returns:
            None.
        """
        self.dispatched.extend(events)


class RecordingNotifier(UserNotifier):
    """Records the wording of every message.

    Args:
        None.

    Returns:
        None.
    """

    def __init__(self) -> None:
        self.wording: list[str] = []

    async def notify(self, user_id: object, notification: Notification) -> None:
        """Record one message.

        Args:
            user_id: Recipient of the message.
            notification: Message about to be sent.

        Returns:
            None.
        """
        del user_id
        self.wording.append(f"{notification.severity()}:{notification.text()}")


class StubNotifications(NotificationFactory):
    """Builds the wording of every message from a template.

    Args:
        None.

    Returns:
        None.
    """

    def board_online(self) -> Notification:
        """Wording of a board coming back.

        Returns:
            Notification: The message the user reads.
        """
        return _StubNotification("board arrived")

    def board_offline(self) -> Notification:
        """Wording of a board going away.

        Returns:
            Notification: The message the user reads.
        """
        return _StubNotification("board left")

    def scenario_started(self, scenario_id: str, target: object) -> Notification:
        """Wording of a scenario starting.

        Args:
            scenario_id: Identifier of the scenario.
            target: What the scenario is about.

        Returns:
            Notification: The message the user reads.
        """
        del target
        return _StubNotification(f"started:{scenario_id}")

    def scenario_progress(self, scenario_id: str, temperature: object) -> Notification:
        """Wording of a scenario making progress.

        Args:
            scenario_id: Identifier of the scenario.
            temperature: What the sensors saw.

        Returns:
            Notification: The message the user reads.
        """
        del temperature
        return _StubNotification(f"progress:{scenario_id}")

    def scenario_finished(self, scenario_id: str, reason: str) -> Notification:
        """Wording of a scenario finishing.

        Args:
            scenario_id: Identifier of the scenario.
            reason: Why it finished.

        Returns:
            Notification: The message the user reads.
        """
        return _StubNotification(f"finished:{scenario_id}:{reason}")

    def scenario_failed(self, scenario_id: str, reason: str) -> Notification:
        """Wording of a scenario failing.

        Args:
            scenario_id: Identifier of the scenario.
            reason: Why it failed.

        Returns:
            Notification: The message the user reads.
        """
        return _StubNotification(f"failed:{scenario_id}:{reason}")


class _StubNotification(Notification):
    """A notification whose severity and text the test reads back.

    Args:
        wording: Text the user would receive.

    Returns:
        None.
    """

    def __init__(self, wording: str) -> None:
        """Remember the wording.

        Args:
            wording: Text the user would receive.

        Returns:
            None.
        """
        self._wording = wording

    def text(self) -> str:
        """Return the wording.

        Returns:
            str: The text of the message.
        """
        return self._wording

    def severity(self) -> str:
        """Return the severity.

        Returns:
            str: The seriousness of the message.
        """
        return "info"


def make_service(
    devices: list[Device],
    scenarios: list[Scenario],
    board: SelectiveBoardGateway,
) -> tuple[
    ScenarioService,
    DeviceRepository,
    ScenarioRepository,
    RecordingRealtime,
    RecordingNotifier,
]:
    """Wire the whole service with the fakes of this module.

    Args:
        devices: Devices the home has.
        scenarios: Scenarios the home already holds.
        board: Gateway deciding which boards answer.

    Returns:
        tuple: Service and the fakes the assertions look into.
    """
    state = HomeState(user_id=UserId.parse(OWNER_UUID), board_online=True)
    device_repo = DeviceRepository(devices)
    scenario_repo = ScenarioRepository(scenarios)
    uow = FakeUow(device_repo, scenario_repo)
    factory = FakeFactory(uow)
    realtime = RecordingRealtime()
    dispatcher = RecordingDispatcher()
    notifier = RecordingNotifier()
    store = StubStateStore(state)
    control = DeviceControlService(
        home_uow=factory,
        boards=board,
        state_store=store,
        realtime=realtime,
        dispatcher=dispatcher,
        clock=FixedClock(),
        selector=DeviceSelector(),
    )
    service = ScenarioService(
        home_uow=factory,
        control=control,
        state_store=store,
        realtime=realtime,
        dispatcher=dispatcher,
        notifier=notifier,
        notifications=StubNotifications(),
        clock=FixedClock(),
        summary_window_sec=300,
    )
    return service, device_repo, scenario_repo, realtime, notifier


def due_scenario(
    capability: Capability, user_id: UserId | None = None, *, delay_minutes: int = 0
) -> Scenario:
    """Schedule the scenario the tests move forward.

    Args:
        capability: Action the scenario performs against the home.
        user_id: Owner of the scenario, defaults to the shared owner.
        delay_minutes: How long to wait before the start, in minutes.

    Returns:
        Scenario: Pending scenario at the start moment.
    """
    return Scenario.schedule(
        user_id=user_id or UserId.parse(OWNER_UUID),
        created_at=NOW,
        delay_minutes=delay_minutes,
        actions=(ScenarioAction(capability=capability),),
        completion_behavior=CompletionBehavior.LEAVE_TO_AUTOMATION,
    )


async def test_advance_marks_a_failing_scenario_failed_and_carries_on():
    lamp = make_device()
    broken = due_scenario(Capability.COOL, delay_minutes=0)
    healthy = due_scenario(Capability.ON, delay_minutes=0)
    board = SelectiveBoardGateway(refused=set())
    service, _devices, _scenarios, _realtime, notifier = make_service(
        [lamp], [broken, healthy], board
    )

    await service.advance(lamp.user_id)

    assert broken.status is ScenarioStatus.FAILED
    assert healthy.status is ScenarioStatus.RUNNING
    assert any(w.startswith("info:failed:") for w in notifier.wording)
    assert any(w.startswith("info:started:") for w in notifier.wording)


async def test_advance_records_running_only_after_the_commands_worked():
    lamp = make_device()
    scenario_on_lamp = due_scenario(Capability.ON, delay_minutes=0)
    board = SelectiveBoardGateway(refused={lamp.id})
    service, _devices, scenarios, _realtime, notifier = make_service(
        [lamp], [scenario_on_lamp], board
    )

    await service.advance(scenario_on_lamp.user_id)

    assert scenario_on_lamp.status is ScenarioStatus.FAILED
    assert board.driven == []
    assert [update.status for update in scenarios.updates] == [ScenarioStatus.FAILED]
    assert any("board_unreachable" in w for w in notifier.wording)
    assert not any(w.startswith("info:started:") for w in notifier.wording)
