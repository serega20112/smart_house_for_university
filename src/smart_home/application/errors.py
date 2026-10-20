"""Failures that belong to the application layer.

The domain declares what the model refuses; this module declares what the
application refuses once it has met the outside world. A login that does not match
a stored hash is not an invariant of an aggregate, and neither is a duplicate
login or a device that a repository could not find, so none of them belong to the
domain.

Presentation maps each type of this module onto an HTTP status once, in one
handler table. Nothing else in the system needs to know a status code.
"""

from __future__ import annotations

from typing import Any

from smart_home.application.ports.language import ClarificationReason
from smart_home.domain.exceptions import (
    ChannelConflictError,
    ClaimAlreadyTakenError,
    ClaimExpiredError,
    DomainError,
    IllegalScenarioTransitionError,
    InvalidDashboardLayoutError,
    InvalidDeviceNameError,
    InvalidDisplayNameError,
    InvalidEmailError,
    InvalidNetworkProfileError,
    InvalidPairingKeyError,
    InvalidRelayChannelError,
    InvalidTemperatureError,
    MalformedIdentifierError,
    NoDeviceForCapabilityError,
    ScenarioAlreadyFinishedError,
    UnsupportedCapabilityError,
    WeakPasswordError,
)
from smart_home.domain.identifiers import DeviceId, EspDeviceId, ScenarioId, UserId

__all__ = [
    "AccountNotFoundError",
    "ApplicationError",
    "BoardNotFoundError",
    "BoardUnreachableError",
    "ChannelConflictError",
    "ClaimAlreadyTakenError",
    "ClaimExpiredError",
    "ClaimNotFoundError",
    "CommandNotUnderstoodError",
    "DeviceNotFoundError",
    "DomainError",
    "EmailAlreadyTakenError",
    "IllegalScenarioTransitionError",
    "InvalidCredentialsError",
    "InvalidDashboardLayoutError",
    "InvalidDeviceNameError",
    "InvalidDisplayNameError",
    "InvalidEmailError",
    "InvalidNetworkProfileError",
    "InvalidPairingKeyError",
    "InvalidRelayChannelError",
    "InvalidTemperatureError",
    "MalformedIdentifierError",
    "NoDeviceForCapabilityError",
    "ScenarioAlreadyFinishedError",
    "ScenarioNotFoundError",
    "UnsupportedCapabilityError",
    "WeakPasswordError",
]


class ApplicationError(Exception):
    """Base class of every failure produced by the application layer."""


class InvalidCredentialsError(ApplicationError):
    """The login does not match a stored account.

    The same error answers both an unknown login and a wrong password, so the
    reply never reveals whether an account exists.

    Args:
        None.

    Returns:
        None.
    """

    def __init__(self) -> None:
        super().__init__("login or password is wrong")


class EmailAlreadyTakenError(ApplicationError):
    """Another account already uses the requested login.

    Args:
        email: Requested login.

    Returns:
        None.
    """

    def __init__(self, email: str) -> None:
        super().__init__(f"email {email} is already registered")
        self.email = email


class AccountNotFoundError(ApplicationError):
    """No account matches the requested identifier.

    Args:
        user_id: Identifier that could not be resolved.

    Returns:
        None.
    """

    def __init__(self, user_id: UserId) -> None:
        super().__init__(f"account {user_id} does not exist")
        self.user_id = user_id


class DeviceNotFoundError(ApplicationError):
    """The account has no device with that identifier.

    Args:
        device_id: Identifier that could not be resolved.

    Returns:
        None.
    """

    def __init__(self, device_id: DeviceId) -> None:
        super().__init__(f"device {device_id} does not exist")
        self.device_id = device_id


class ScenarioNotFoundError(ApplicationError):
    """The account has no scenario with that identifier.

    Args:
        scenario_id: Identifier that could not be resolved.

    Returns:
        None.
    """

    def __init__(self, scenario_id: ScenarioId) -> None:
        super().__init__(f"scenario {scenario_id} does not exist")
        self.scenario_id = scenario_id


class BoardNotFoundError(ApplicationError):
    """The account has no board with that identifier.

    Args:
        board_id: Identifier that could not be resolved.

    Returns:
        None.
    """

    def __init__(self, board_id: EspDeviceId) -> None:
        super().__init__(f"board {board_id} does not exist")
        self.board_id = board_id


class ClaimNotFoundError(ApplicationError):
    """No open offer carries the presented token.

    Args:
        token: Token that could not be resolved.

    Returns:
        None.
    """

    def __init__(self, token: str) -> None:
        super().__init__(f"no announced board carries the token {token}")
        self.token = token


class BoardUnreachableError(ApplicationError):
    """The board behind a device did not answer.

    Args:
        reason: Machine readable reason reported by the transport.

    Returns:
        None.
    """

    def __init__(self, reason: str) -> None:
        super().__init__(f"the board did not accept the command: {reason}")
        self.reason = reason


class ConcurrentModificationError(ApplicationError):
    """Another writer changed an aggregate under this one.

    A writer that read an older revision of a row has no say in how the row
    looks now: the store refuses its stale write. The caller is expected to read
    the fresh snapshot and state its intent again rather than to overwrite a
    change it never saw.

    Args:
        aggregate: Human readable name of the aggregate.
        aggregate_id: Identifier of the aggregate that moved on.

    Returns:
        None.
    """

    def __init__(self, aggregate: str, aggregate_id: object) -> None:
        super().__init__(f"{aggregate} {aggregate_id} changed under this writer")
        self.aggregate = aggregate
        self.aggregate_id = aggregate_id


class CommandNotUnderstoodError(ApplicationError):
    """The free form command cannot be carried out as it stands.

    Args:
        reason: Why the command cannot be carried out.
        details: What the user has to add or change.

    Returns:
        None.
    """

    def __init__(self, reason: ClarificationReason, **details: Any) -> None:
        super().__init__(f"command needs clarification: {reason.value}")
        self.reason = reason
        self.details = details
