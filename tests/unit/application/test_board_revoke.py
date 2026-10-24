"""Leaving a board never erases the home without asking.

A board goes away, but the devices standing on its channels are the person's
work: their names, capabilities and automation. The service therefore refuses to
remove a board that still owns devices until the caller says what happens to
them, and whatever it says is done in the same transaction that removes the
board.
"""

from __future__ import annotations

import pytest
from tests.conftest import make_device

from backend.application.dto.boards.detach_policy import DetachPolicy
from backend.application.errors import BoardHasDevicesError, BoardNotFoundError
from backend.application.interfaces.unit_of_work.board_onboarding import (
    BoardOnboardingUnitOfWork,
)
from backend.application.services.board_onboarding import BoardOnboardingService
from backend.domain.aggregates.device.device import Device
from backend.domain.identifiers import EspDeviceId, UserId


class StubBoards:
    """A board store that knows exactly one board, or none at all.

    Args:
        exists: Whether the account still owns the board.
    """

    def __init__(self, exists: bool = True) -> None:
        self.exists = exists
        self.deleted = 0

    async def get(self, user_id: UserId, board_id: EspDeviceId) -> object | None:
        del user_id, board_id
        return object() if self.exists else None

    async def delete(self, user_id: UserId, board_id: EspDeviceId) -> bool:
        del user_id, board_id
        self.deleted += 1
        return self.exists


class StubDevices:
    """A device store holding the devices one board is about to leave.

    Args:
        devices: Devices standing on the channels of that board.
    """

    def __init__(self, devices: list[Device]) -> None:
        self.devices = devices
        self.updated: list[Device] = []
        self.deleted = 0

    async def list_for_board(self, user_id: UserId, board_id: EspDeviceId) -> list[Device]:
        del user_id, board_id
        return list(self.devices)

    async def update(self, device: Device) -> None:
        self.updated.append(device)

    async def delete_for_board(self, user_id: UserId, board_id: EspDeviceId) -> int:
        del user_id, board_id
        self.deleted += len(self.devices)
        return len(self.devices)


class StubUnitOfWork(BoardOnboardingUnitOfWork):
    """A transaction that hands out the stubs and counts commits.

    Args:
        boards: Board store of this transaction.
        devices: Device store of this transaction.
    """

    def __init__(self, boards: StubBoards, devices: StubDevices) -> None:
        self._boards = boards
        self._devices = devices
        self.commits = 0

    @property
    def boards(self) -> StubBoards:
        """Return the board store of this transaction.

        Returns:
            StubBoards: The board stub.
        """
        return self._boards

    @property
    def devices(self) -> StubDevices:
        """Return the device store of this transaction.

        Returns:
            StubDevices: The device stub.
        """
        return self._devices

    @property
    def claims(self) -> object:
        """The claim store is never read by the revoke path.

        Raises:
            NotImplementedError: Always, as no claim is taken here.
        """
        raise NotImplementedError

    @property
    def networks(self) -> object:
        """The network store is never read by the revoke path.

        Raises:
            NotImplementedError: Always, as no network is written here.
        """
        raise NotImplementedError

    async def commit(self) -> None:
        """Confirm the block.

        Returns:
            None.
        """
        self.commits += 1

    async def rollback(self) -> None:
        """Undo the block, which the stubs do not need.

        Returns:
            None.
        """


def service_over(uow: StubUnitOfWork) -> BoardOnboardingService:
    """Build the onboarding service over one prepared transaction.

    Args:
        uow: Transaction every call of the service opens.

    Returns:
        BoardOnboardingService: Service whose revoke path is under test.
    """
    return BoardOnboardingService(
        onboarding_uow=lambda: uow,
        queries=object(),
        boards=object(),
        realtime=object(),
        clock=object(),
        claim_ttl_sec=60,
    )


async def test_board_with_devices_is_refused_until_decision_is_made() -> None:
    devices = [make_device(name="Lamp"), make_device(name="Heater", channel=4)]
    boards = StubBoards()
    uow = StubUnitOfWork(boards, StubDevices(devices))
    service = service_over(uow)

    with pytest.raises(BoardHasDevicesError) as raised:
        await service.revoke(UserId.generate(), EspDeviceId.generate())

    assert raised.value.devices == ("Lamp", "Heater")
    assert boards.deleted == 0
    assert uow.commits == 0


async def test_detach_leaves_devices_in_the_home_without_a_board() -> None:
    devices = [make_device(name="Lamp")]
    boards = StubBoards()
    store = StubDevices(devices)
    uow = StubUnitOfWork(boards, store)
    service = service_over(uow)

    await service.revoke(UserId.generate(), EspDeviceId.generate(), DetachPolicy.DETACH)

    assert [device.board_id for device in store.updated] == [None]
    assert store.deleted == 0
    assert boards.deleted == 1
    assert uow.commits == 1


async def test_delete_policy_removes_devices_together_with_the_board() -> None:
    devices = [make_device(name="Lamp"), make_device(name="Heater", channel=4)]
    boards = StubBoards()
    store = StubDevices(devices)
    uow = StubUnitOfWork(boards, store)
    service = service_over(uow)

    await service.revoke(UserId.generate(), EspDeviceId.generate(), DetachPolicy.DELETE)

    assert store.deleted == 2
    assert store.updated == []
    assert boards.deleted == 1
    assert uow.commits == 1


async def test_board_without_devices_leaves_without_a_decision() -> None:
    boards = StubBoards()
    store = StubDevices([])
    uow = StubUnitOfWork(boards, store)
    service = service_over(uow)

    await service.revoke(UserId.generate(), EspDeviceId.generate())

    assert boards.deleted == 1
    assert uow.commits == 1


async def test_unknown_board_is_reported_as_missing() -> None:
    boards = StubBoards(exists=False)
    uow = StubUnitOfWork(boards, StubDevices([]))
    service = service_over(uow)

    with pytest.raises(BoardNotFoundError):
        await service.revoke(UserId.generate(), EspDeviceId.generate(), DetachPolicy.DELETE)

    assert boards.deleted == 0
    assert uow.commits == 0
