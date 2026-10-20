"""A lost race of a device change is retried on a fresh snapshot.

The use case states its change though the store, and the store decides whether
this writer still owns the revision it read. The tests here stand in for the
store: the first attempts lose a race the way the store would settle it, and
the use case is expected to read the newest snapshot and win.
"""

import pytest
from tests.conftest import make_device

from smart_home.application.dto.device import UpdateDeviceCommand
from smart_home.application.errors import ConcurrentModificationError
from smart_home.application.ports.unit_of_work.home import HomeUnitOfWork
from smart_home.application.use_cases.devices.update_device import UpdateDeviceUseCase
from smart_home.domain.devices.device import Device


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


async def test_update_device_retries_on_a_lost_race_and_publishes_once():
    device = make_device()
    repository = RaceRepository(device, races_lost=1)
    factory = SequenceFactory(repository)
    realtime = RecordingRealtime()
    use_case = UpdateDeviceUseCase(factory, realtime, RecordingDispatcher())

    view = await use_case.execute(
        device.user_id, device.id, UpdateDeviceCommand(name="Reading lamp")
    )

    assert view.name == "Reading lamp"
    assert repository.races_lost == 0
    assert factory.opened == 2
    assert realtime.published == ["devices.updated"]


async def test_update_device_gives_up_after_repeated_lost_races():
    device = make_device()
    repository = RaceRepository(device, races_lost=99)
    factory = SequenceFactory(repository)
    realtime = RecordingRealtime()
    use_case = UpdateDeviceUseCase(factory, realtime, RecordingDispatcher())

    with pytest.raises(ConcurrentModificationError):
        await use_case.execute(device.user_id, device.id, UpdateDeviceCommand(name="Reading lamp"))

    assert factory.opened == 3
    assert realtime.published == []
