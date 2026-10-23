"""Доменные решатели: выбор устройства и расчёт требования климату."""

from __future__ import annotations

from dishka import Provider, Scope, provide

from backend.domain.policies.climate_policy import DemandCalculator
from backend.domain.policies.device_selector import DeviceSelector

APP = Scope.APP


class DomainProvider(Provider):
    """Решения, к которым прикладной слой обращается как к сервисам домена."""

    @provide(scope=APP)
    def device_selector(self) -> DeviceSelector:
        """Собирает решатель того, для какого устройства команда."""
        return DeviceSelector()

    @provide(scope=APP)
    def demand_calculator(self) -> DemandCalculator:
        """Собирает решатель того, на что настроен климат."""
        return DemandCalculator()
