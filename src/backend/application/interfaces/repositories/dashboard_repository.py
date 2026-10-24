"""Хранилище раскладки дашборда одного аккаунта."""

from __future__ import annotations

from backend.application.interfaces.repositories.base import Loader, Saver
from backend.domain.aggregates.dashboard.dashboard_state import DashboardState


class DashboardRepository(Loader[DashboardState], Saver[DashboardState]):
    """Раскладка панели: одна строка на аккаунт."""
