"""Automation and scenario scheduling settings."""

from __future__ import annotations

import os


def interval_sec() -> float:
    """Return the period of one automation cycle.

    Returns:
        float: Period in seconds.
    """
    return float(os.getenv("AUTOMATION_INTERVAL_SEC", "10.0"))


def scenario_tick_sec() -> float:
    """Return the period of one scenario tick.

    Returns:
        float: Period in seconds.
    """
    return float(os.getenv("AUTOMATION_SCENARIO_TICK_SEC", "5.0"))


def manual_override_minutes() -> int:
    """Return how long manual control suspends automation.

    Returns:
        int: Override duration in minutes.
    """
    return int(os.getenv("AUTOMATION_MANUAL_OVERRIDE_MINUTES", "30"))


def scenario_summary_minutes() -> int:
    """Return the interval between progress notifications of a running scenario.

    Returns:
        int: Summary interval in minutes.
    """
    return int(os.getenv("AUTOMATION_SCENARIO_SUMMARY_MINUTES", "10"))
