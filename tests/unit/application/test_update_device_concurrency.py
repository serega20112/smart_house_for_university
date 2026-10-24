"""A lost race of a device change is retried on a fresh snapshot.

The use case states its change though the store, and the store decides whether
this writer still owns the revision it read. The tests here stand in for the
store: the first attempts lose a race the way the store would settle it, and
the use case is expected to read the newest snapshot and win.
"""

from collections.abc import Sequence
from datetime import datetime

import pytest
from tests.conftest import make_device

from backend.application.dto.devices.update_device_command import UpdateDeviceCommand
from backend.application.errors import ConcurrentModificationError
from backend.application.interfaces.services.state.home_state_store import HomeStateStore
from backend.application.interfaces.unit_of_work.home import HomeUnitOfWork
from backend.application.use_cases.devices.update_device import UpdateDeviceUseCase
from backend.domain.aggregates.device.device import Device
from backend.domain.entities.home_state.home_state import HomeState
from backend.domain.identifiers import DeviceId, EspDeviceId, UserId
from backend.domain.value_objects.climate.climate_reading import ClimateReading
from backend.domain.value_objects.devices.device_status import DeviceStatus
from backend.domain.value_objects.devices.relay_state import RelayState

BOARD = EspDeviceId.generate()


class RaceRepository:
    """A lossy stand-in for the store.

    A writer that names an obsolete revision raises the refusal the store
    raises and, like the real store's racing neighbour, commits its own change
    meanwhile.

    Args:
        device: The only device this repository knows.
        races_lost: How many writers hit a stale revision before one wins.
    """

    def __init__(self, device: Device, races_lost: int) -> None:
        self.device = device
        self.races_lost = races_lost
        self.attempts: list[int] = []

    async def get(self, user_id: object, device_id: object) -> Device | None:
        del user_id, device_id
        return self.device

    async def update(self, device: Device) -> None:
        self.attempts.append(device.version)
        if self.races_lost > 0:
            self.races_lost -= 1
            self.device.version += 1
            raise ConcurrentModificationError("device", device.id)
        device.version += 1


class RacingStore(HomeUnitOfWork):
    """A transaction over the one repository that races with itself.

    Args:
        repository: Lossy stand-in the use case talks to.

    Returns:
        None.
    """

    def __init__(self, repository: RaceRepository) -> None:
        self._repository = repository

    @property
    def devices(self) -> RaceRepository:
        """Return the repository of this transaction.

        Returns:
            RaceRepository: The lossy stand-in.
        """
        return self._repository

    @property
    def boards(self) -> object:
        """The board repository is never used by the change under test.

        Raises:
            NotImplementedError: Always, as no device names a board here.
        """
        raise NotImplementedError

    @property
    def automation(self) -> object:
        raise NotImplementedError

    @property
    def scenarios(self) -> object:
        raise NotImplementedError

    @property
    def dashboard(self) -> object:
        raise NotImplementedError

    @property
    def preferences(self) -> object:
        raise NotImplementedError

    async def commit(self) -> None:
        """Confirm the block.

        Returns:
            None.
        """

    async def rollback(self) -> None:
        """Undo the block.

        Returns:
            None.
        """


class SequenceFactory:
    """Hands each call of the use case a fresh transaction.

    A retry loop must open a new transaction per try, so the factory records how
    often it was asked.

    Args:
        repository: Lossy stand-in every transaction shares.

    Returns:
        None.
    """

    def __init__(self, repository: RaceRepository) -> None:
        self._repository = repository
        self.opened = 0

    def __call__(self) -> RacingStore:
        self.opened += 1
        return RacingStore(self._repository)


class RecordingRealtime:
    """Records what was published.

    Args:
        None.

    Returns:
        None.
    """

    def __init__(self) -> None:
        self.published: list[str] = []

    async def publish(self, user_id: object, event: str, payload: object) -> None:
        del user_id, payload
        self.published.append(event)

    async def broadcast(self, event: object, payload: object) -> None:
        del event, payload


class RecordingDispatcher:
    """Records what was handed to the reactions.

    Args:
        None.

    Returns:
        None.
    """

    def __init__(self) -> None:
        self.dispatched: list[object] = []

    async def dispatch(self, events: object) -> None:
        self.dispatched.extend(events)


class LiveStateStore(HomeStateStore):
    """State store that always answers with one prepared state.

    Args:
        state: Home state every read returns.

    Returns:
        None.
    """

    def __init__(self, state: HomeState) -> None:
        self._state = state

    async def read(self, user_id: UserId) -> HomeState:
        del user_id
        return self._state

    async def record_background_reading(
        self,
        user_id: UserId,
        board_id: EspDeviceId,
        reading: ClimateReading,
        changed_at: datetime,
    ) -> ClimateReading:
        del user_id, board_id, reading, changed_at
        return ClimateReading()

    async def record_relay_report(
        self,
        user_id: UserId,
        board_id: EspDeviceId,
        states: Sequence[bool],
        changed_at: datetime,
    ) -> tuple[int, ...]:
        del user_id, board_id, states, changed_at
        return ()

    async def record_board_online(
        self, user_id: UserId, board_id: EspDeviceId, online: bool, changed_at: datetime
    ) -> bool:
        del user_id, board_id, changed_at
        return online

    async def record_command_result(
        self,
        user_id: UserId,
        board_id: EspDeviceId,
        device_id: DeviceId,
        channel: int,
        status: DeviceStatus,
        changed_at: datetime,
    ) -> None:
        del user_id, board_id, device_id, channel, status, changed_at

    async def forget_device_status(self, user_id: UserId, device_id: DeviceId) -> None:
        del user_id, device_id

    async def set_override_until(self, user_id: UserId, until: datetime | None) -> None:
        del user_id, until

    async def claim_summary_slot(self, user_id: UserId, key: str, window_sec: int) -> bool:
        del user_id, key, window_sec
        return True


async def test_update_device_retries_on_a_lost_race_and_publishes_once():
    device = make_device(board_id=BOARD)
    repository = RaceRepository(device, races_lost=1)
    factory = SequenceFactory(repository)
    realtime = RecordingRealtime()
    state = HomeState(
        user_id=device.user_id,
        online_boards=frozenset({BOARD}),
        relay_states={BOARD: {int(device.channel): RelayState.ON}},
        device_modes={device.id: DeviceStatus.ACTIVE},
    )
    use_case = UpdateDeviceUseCase(
        factory, realtime, RecordingDispatcher(), LiveStateStore(state), refresh_attempts=3
    )

    view = await use_case.execute(
        device.user_id, device.id, UpdateDeviceCommand(name="Reading lamp")
    )

    assert view.name == "Reading lamp"
    assert view.status is DeviceStatus.ACTIVE
    assert repository.races_lost == 0
    assert factory.opened == 2
    assert realtime.published == ["devices.updated"]


async def test_update_device_gives_up_after_repeated_lost_races():
    device = make_device()
    repository = RaceRepository(device, races_lost=99)
    factory = SequenceFactory(repository)
    realtime = RecordingRealtime()
    use_case = UpdateDeviceUseCase(
        factory,
        realtime,
        RecordingDispatcher(),
        LiveStateStore(HomeState(user_id=device.user_id)),
        refresh_attempts=3,
    )

    with pytest.raises(ConcurrentModificationError):
        await use_case.execute(device.user_id, device.id, UpdateDeviceCommand(name="Reading lamp"))

    assert factory.opened == 3
    assert realtime.published == []
