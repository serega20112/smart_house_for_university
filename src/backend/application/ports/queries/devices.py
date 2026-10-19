"""Read side of the device configuration.

A query returns a flat row shaped for display instead of an aggregate. That is the
whole point of the read side: the interface never has to walk a device to render
it, and a screen never has to open a transaction.

Read models are declared in :mod:`backend.application.dto` and the queries return
them, so neither the storage layer nor the interface decides what a row looks
like.
"""

from __future__ import annotations

from typing import Protocol

from backend.application.dto.device import DeviceView
from backend.domain.identifiers import DeviceId, UserId


class DeviceQueries(Protocol):
    """Reads of the device configuration."""

    async def list_all(self, user_id: UserId) -> list[DeviceView]:
        """Return every device of an account.

        Args:
            user_id: Owner of the devices.

        Returns:
            list[DeviceView]: Devices shaped for display.
        """

    async def get(self, user_id: UserId, device_id: DeviceId) -> DeviceView | None:
        """Return one device of an account.

        Args:
            user_id: Owner of the device.
            device_id: Identifier of the device.

        Returns:
            DeviceView | None: Device, or None when the account has no such one.
        """
