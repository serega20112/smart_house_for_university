"""The network a board is told to use.

A board that was set up on its own already has a network, and the backend learns
which one from the handshake. This aggregate is the other half: the network the
owner asked for in the interface and the backend hands to the board.

The two are kept apart on purpose. What the board reports is what it is on right
now and lives with the board itself, while this is what it is to be on, and the
two differ while a change is on its way.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from smart_home.domain.boards.network_profile import NetworkProfile
from smart_home.domain.identifiers import EspDeviceId, UserId


@dataclass(frozen=True, slots=True)
class BoardNetwork:
    """The network one board is to use.

    Args:
        board_id: Board the network belongs to.
        user_id: Owner of the board.
        profile: Settings the backend asked the board to use.
        updated_at: Moment the settings were written.

    Returns:
        None.
    """

    board_id: EspDeviceId
    user_id: UserId
    profile: NetworkProfile
    updated_at: datetime
