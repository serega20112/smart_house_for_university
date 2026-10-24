"""Новая раскладка главного экрана."""

from __future__ import annotations

from dataclasses import dataclass

from backend.domain.entities.personalization.dashboard_widget import DashboardWidget


@dataclass(frozen=True, slots=True)
class DashboardPatch:
    """Раскладка, которую просят интерфейс сохранить.

    Attributes:
        widgets: Карточки в порядке вывода.
    """

    widgets: tuple[DashboardWidget, ...]
