"""Why an automation demand was not performed."""

from __future__ import annotations

from enum import StrEnum


class SkipReason(StrEnum):
    """Reason a climate demand was skipped during an automation cycle.

    These are the situations in which the model declines to act on a demand
    that the calculator did emit: the home does not want automation right now,
    a person overrode it manually, or there is no usable sensor reading to
    drive a decision.
    """

    AUTOMATION_DISABLED = "automation_disabled"
    MANUAL_CONTROL_ACTIVE = "manual_control_active"
    NO_SENSOR_DATA = "no_sensor_data"
    NO_SUITABLE_DEVICE = "no_suitable_device"
