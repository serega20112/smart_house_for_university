"""Scenario lifecycle policy."""

from __future__ import annotations

from datetime import datetime

from smart_home_backend.domain.entities.scenario import Scenario
from smart_home_backend.domain.enums.device import DeviceStatus
from smart_home_backend.domain.enums.device import Capability

GOAL_TOLERANCE_C = 0.5

STATUS_TO_CAPABILITY: dict[DeviceStatus, Capability] = {
    DeviceStatus.ON: Capability.ON,
    DeviceStatus.OFF: Capability.OFF,
    DeviceStatus.COOL: Capability.COOL,
    DeviceStatus.HEAT: Capability.HEAT,
}


def is_goal_reached(scenario: Scenario, temperature: float | None) -> bool:
    """Return whether the climate goal of the scenario is satisfied.

    Args:
        scenario: Scenario being evaluated.
        temperature: Current temperature or None when unavailable.

    Returns:
        bool: True when every target value is reached.
    """
    if not scenario.actions or temperature is None:
        return False
    for action in scenario.actions:
        if action.target_value is None:
            continue
        if abs(temperature - action.target_value) > GOAL_TOLERANCE_C:
            return False
    return True


def has_timed_out(scenario: Scenario, now: datetime) -> bool:
    """Return whether the scenario duration has elapsed.

    Args:
        scenario: Scenario being evaluated.
        now: Current moment.

    Returns:
        bool: True when the scenario ran out of time.
    """
    return scenario.is_expired(now)
