"""Device repository port."""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Sequence

from smart_home_backend.domain.entities.device import Device


class DeviceRepository(ABC):
    """Access to the configuration of logical devices."""

    @abstractmethod
    async def list_all(self) -> Sequence[Device]:
        """Return every configured device ordered by id.

        Returns:
            Sequence[Device]: Configured devices.
        """

    @abstractmethod
    async def get(self, device_id: int) -> Device | None:
        """Return a device by id.

        Args:
            device_id: Identifier of the device.

        Returns:
            Device | None: Device or None when it does not exist.
        """

    @abstractmethod
    async def get_by_channel(self, channel: int) -> Device | None:
        """Return the device bound to a physical relay channel.

        Args:
            channel: Physical relay channel.

        Returns:
            Device | None: Device or None when the channel is unassigned.
        """

    @abstractmethod
    async def save(self, device: Device) -> Device:
        """Create or update a device.

        Args:
            device: Device to persist.

        Returns:
            Device: Persisted device including its identifier.
        """

    @abstractmethod
    async def delete(self, device_id: int) -> bool:
        """Delete a device.

        Args:
            device_id: Identifier of the device.

        Returns:
            bool: True when a device was removed.
        """

    @abstractmethod
    async def channel_in_use(self, channel: int, exclude_id: int | None = None) -> bool:
        """Return whether a physical channel is already taken.

        Args:
            channel: Physical relay channel.
            exclude_id: Device that is allowed to keep the channel.

        Returns:
            bool: True when another device already uses the channel.
        """
