"""Contracts of the board operations."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from backend.domain.identifiers import EspClaimId, EspDeviceId


@dataclass(frozen=True, slots=True)
class SetNetworkCommand:
    """The network a board is told to use.

    Args:
        ssid: Name of the wireless network.
        password: Password of that network, empty when the network is open.
        host: Address of the server the board reports to.
        server_port: Port of the ordinary interface of that server.
        socket_port: Port of the board socket of that server.
        socket_path: Path of the board socket of that server.

    Returns:
        None.
    """

    ssid: str
    password: str
    host: str
    server_port: int
    socket_port: int
    socket_path: str


@dataclass(frozen=True, slots=True)
class BoardNetworkView:
    """The network of a board as the interface needs it.

    The password is deliberately absent: it is a secret, and a secret has no
    business in a screen. The board keeps it in its own flash.

    Args:
        board_id: Identifier of the board.
        ssid: Name of the wireless network the board is told to use.
        host: Address of the server the board is told to report to.
        server_port: Port of the ordinary interface of that server.
        socket_port: Port of the board socket of that server.
        socket_path: Path of the board socket of that server.
        configured: Whether the board already has a network of its own.
        updated_at: Moment the settings were written, or None.

    Returns:
        None.
    """

    board_id: EspDeviceId
    ssid: str
    host: str
    server_port: int
    socket_port: int
    socket_path: str
    configured: bool
    updated_at: datetime | None


@dataclass(frozen=True, slots=True)
class AnnounceBoardCommand:
    """What a board said about itself while dialing in.

    Args:
        device_key: Secret the board presented.
        label: Short code the board reported, or an empty string.

    Returns:
        None.
    """

    device_key: str
    label: str


@dataclass(frozen=True, slots=True)
class PairBoardCommand:
    """A board the user paired from the interface.

    Args:
        name: Name shown to the user.
        pairing_key: Key chosen by the user, or None to let the system generate
            one.

    Returns:
        None.
    """

    name: str
    pairing_key: str | None = None


@dataclass(frozen=True, slots=True)
class ClaimBoardCommand:
    """A board the user is taking over from the interface.

    Args:
        claim_token: Token of the offer shown next to the board.
        name: Name the user wants the board to have.

    Returns:
        None.
    """

    claim_token: str
    name: str


@dataclass(frozen=True, slots=True)
class BoardView:
    """One board as the interface needs it.

    The pairing key is deliberately absent: it is a credential, and a credential has
    no business in a screen that lists boards. It is returned exactly once, by the
    pairing operation itself.

    Args:
        id: Identifier of the board.
        name: Name shown to the user.
        online: Whether the board is connected right now.
        last_seen_at: Moment of the last successful handshake, or None.
        current_ssid: Network the board reported being on, or None.

    Returns:
        None.
    """

    id: EspDeviceId
    name: str
    online: bool
    last_seen_at: datetime | None
    current_ssid: str | None = None


@dataclass(frozen=True, slots=True)
class BoardClaimView:
    """One offer as the interface needs it.

    The device key is never part of the answer: it is the credential of the board,
    and the only things a person needs are the code and the token of the offer.

    Args:
        id: Identifier of the offer.
        label: Short code shown next to the board.
        claim_token: Token the user has to send to take the board.
        announced_at: Moment the board announced itself.
        expires_at: Moment the offer stops being valid.

    Returns:
        None.
    """

    id: EspClaimId
    label: str
    claim_token: str
    announced_at: datetime
    expires_at: datetime


@dataclass(frozen=True, slots=True)
class PairedBoard:
    """A board that was just paired, together with its key.

    Args:
        board: The board as it is now stored.
        pairing_key: Secret the board has to present, returned exactly once.

    Returns:
        None.
    """

    board: BoardView
    pairing_key: str
