"""Why a scenario stopped acting."""

from enum import StrEnum


class FinishReason(StrEnum):
    """Why a scenario stopped acting on the home.

    The wording the interface and the notifications see is exactly the value,
    so a reason that comes back as text in a row reads as a vocabulary here.

    Args:
        None.

    Returns:
        None.
    """

    GOAL_REACHED = "goal_reached"
    DURATION_EXPIRED = "duration_expired"
    CANCELLED_BY_USER = "cancelled_by_user"
    NO_DEVICE_FOR_CAPABILITY = "no_device_for_capability"
    BOARD_UNREACHABLE = "board_unreachable"
