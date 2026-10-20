"""What happens with the devices once a scenario is finished."""

from __future__ import annotations

from enum import StrEnum

from smart_home.domain.devices.device_status import DeviceStatus


class CompletionBehavior(StrEnum):
    """How a finished scenario leaves the home behind.

    Args:
        None.

    Returns:
        None.
    """

    LEAVE_TO_AUTOMATION = "LEAVE_TO_AUTOMATION"
    SWITCH_EVERYTHING_OFF = "SWITCH_EVERYTHING_OFF"
    RESTORE_CAPTURED_STATE = "RESTORE_CAPTURED_STATE"

    def status_to_apply(self, captured_status: DeviceStatus | None) -> DeviceStatus | None:
        """Return the state a device has to be put back into.

        Args:
            captured_status: State the device had before the scenario started,
                or None when nothing was captured for it.

        Returns:
            DeviceStatus | None: State to restore, or None when the device has to
            be left alone.
        """
        if self is CompletionBehavior.LEAVE_TO_AUTOMATION:
            return None
        if self is CompletionBehavior.SWITCH_EVERYTHING_OFF:
            return DeviceStatus.OFF
        return captured_status

    @classmethod
    def parse(cls, raw: object) -> CompletionBehavior:
        """Read a behavior from a value received from the outside.

        Args:
            raw: Behavior name or enum member.

        Returns:
            CompletionBehavior: Parsed behavior.

        Raises:
            ValueError: When the value does not name a behavior.
        """
        if isinstance(raw, cls):
            return raw
        if raw is None:
            raise ValueError("completion behavior is missing")
        return cls(str(raw).strip().upper())
