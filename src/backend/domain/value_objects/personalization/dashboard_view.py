"""Раскладка дашборда в том виде, в каком её показывает экран."""

from __future__ import annotations

from dataclasses import dataclass

from backend.domain.value_objects.personalization.dashboard_widget import DashboardWidget


@dataclass(frozen=True, slots=True)
class DashboardView:
    """Дашборд человека для интерфейса.

    Attributes:
        widgets: Виджеты в порядке вывода.
    """

    widgets: tuple[DashboardWidget, ...]
