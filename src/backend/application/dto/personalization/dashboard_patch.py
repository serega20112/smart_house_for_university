"""A new dashboard layout."""

from __future__ import annotations

from dataclasses import dataclass

from backend.domain.value_objects.personalization.dashboard_widget import DashboardWidget


@dataclass(frozen=True, slots=True)
class DashboardPatch:
    """The layout the interface is asked to store.

    Args:
        widgets: Widgets in the order they have to be rendered.

    Returns:
        None.
    """

    widgets: tuple[DashboardWidget, ...]
