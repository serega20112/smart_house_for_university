"""Port giving the application a view of the configured devices of a home.

The state synchronizer needs to translate a relay number into a device so the
message it announces can carry a name instead of a channel. Asking a repository for
that would mean opening a transaction every time a board reports anything, so the
directory is a cheap read instead.
"""

from __future__ import annotations

from typing import Protocol

from smart_home.domain.devices.device import Device
from smart_home.domain.identifiers import UserId


class HomeDeviceDirectory(Protocol):
    """Cheap reads of the device configuration of one home."""

    async def all_of(self, user_id: UserId) -> list[Device]:
        """Return every device of a home.

        Args:
            user_id: Owner of the home.

        Returns:
            list[Device]: Configured devices.
        """

    async def by_channel(self, user_id: UserId) -> dict[int, Device]:
        """Return the devices of a home indexed by their relay channel.

        Args:
            user_id: Owner of the home.

        Returns:
            dict[int, Device]: Devices mapped to their channel. A channel with no
            device behind it is simply absent.
        """
