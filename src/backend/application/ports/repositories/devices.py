"""Device repository port."""

from __future__ import annotations

from collections.abc import Sequence
from typing import Protocol

from backend.domain.devices.device import Device
from backend.domain.identifiers import DeviceId, UserId


class DeviceRepository(Protocol):
    """Storage of the logical devices of one account.

    Every method is scoped to an owner, so a caller can never reach a device of
    somebody else by guessing its identifier.
    """

    async def list_all(self, user_id: UserId) -> Sequence[Device]:
        """Return every device of an account.

        Args:
            user_id: Owner of the devices.

        Returns:
            Sequence[Device]: Configured devices.
        """

    async def get(self, user_id: UserId, device_id: DeviceId) -> Device | None:
        """Return one device of an account.

        Args:
            user_id: Owner of the device.
            device_id: Identifier of the device.

        Returns:
            Device | None: Device, or None when the account has no such one.
        """

    async def add(self, device: Device) -> None:
        """Store a newly created device.

        Args:
            device: Device to persist.

        Returns:
            None.
        """

    async def update(self, device: Device) -> None:
        """Store a changed device.

        Args:
            device: Device to persist.

        Returns:
            None.
        """

    async def delete(self, user_id: UserId, device_id: DeviceId) -> bool:
        """Remove a device of an account.

        Args:
            user_id: Owner of the device.
            device_id: Identifier of the device.

        Returns:
            bool: True when a device was removed.
        """

    async def channel_taken(
        self, user_id: UserId, channel: int, exclude: DeviceId | None = None
    ) -> bool:
        """Return whether a relay channel is already wired to another device.

        Args:
            user_id: Owner of the devices.
            channel: Physical relay channel.
            exclude: Device that is allowed to keep the channel.

        Returns:
            bool: True when another device of the account already uses it.
        """
