"""Outcome vocabulary of application operations.

Use cases return an outcome instead of raising exceptions, so presentation maps a
machine-readable status onto HTTP codes and user-facing text without duplicating
business rules.
"""

from __future__ import annotations

from smart_home_backend.domain.enums.base import StrEnum


class OperationStatus(StrEnum):
    """Result class of a single application operation."""

    SUCCESS = "SUCCESS"
    NOT_FOUND = "NOT_FOUND"
    UNAVAILABLE = "UNAVAILABLE"
    UNSUPPORTED = "UNSUPPORTED"
    CHANNEL_CONFLICT = "CHANNEL_CONFLICT"
    INVALID_INPUT = "INVALID_INPUT"
    FAILED = "FAILED"

    @property
    def is_success(self) -> bool:
        """Return whether the operation completed successfully.

        Returns:
            bool: True for SUCCESS.
        """
        return self is OperationStatus.SUCCESS


class ClarificationReason(StrEnum):
    """Why the system refuses to execute a command without more detail."""

    UNRECOGNIZED_INTENT = "UNRECOGNIZED_INTENT"
    LOW_CONFIDENCE = "LOW_CONFIDENCE"
    UNKNOWN_DEVICE = "UNKNOWN_DEVICE"
    MISSING_TEMPERATURE = "MISSING_TEMPERATURE"
    MISSING_HUMIDITY = "MISSING_HUMIDITY"
    MISSING_CAPABILITY = "MISSING_CAPABILITY"
