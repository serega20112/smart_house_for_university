"""Почему сценарий перестал действовать."""

from enum import StrEnum


class FinishReason(StrEnum):
    """Причина, по которой сценарий перестал действовать в доме.

    Экран и уведомления видят ровно это значение, поэтому причина, вернувшаяся из
    строки текстом, читается здесь как словарь терминов.
    """

    GOAL_REACHED = "goal_reached"
    DURATION_EXPIRED = "duration_expired"
    CANCELLED_BY_USER = "cancelled_by_user"
    NO_DEVICE_FOR_CAPABILITY = "no_device_for_capability"
    BOARD_UNREACHABLE = "board_unreachable"
