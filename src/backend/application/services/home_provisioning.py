"""Даёт новому аккаунту дом, в котором он живёт.

Это реакция на факт, который аккаунт записал при создании, а не шаг регистрации.
Регистрация умеет создавать аккаунт; что именно появляется вместе с ним —
отдельное решение, и меняется оно без правки регистрации.
"""

from __future__ import annotations

from backend.application.interfaces.unit_of_work.home import HomeUnitOfWorkFactory
from backend.domain.aggregates.automation.automation_settings import AutomationSettings
from backend.domain.aggregates.dashboard.dashboard_state import DashboardState
from backend.domain.entities.personalization.user_preferences import UserPreferences
from backend.domain.events import UserRegistered
from backend.domain.identifiers import UserId
from backend.domain.policies.home_template import STARTER_DEVICES


class HomeProvisioning:
    """Создаёт устройства, панель и настройки нового аккаунта."""

    def __init__(self, home_uow: HomeUnitOfWorkFactory) -> None:
        """Собирает реакцию на создание аккаунта.

        Args:
            home_uow: Граница транзакции над конфигурацией дома.
        """
        self._home_uow = home_uow

    async def __call__(self, events: tuple[object, ...]) -> None:
        """Даёт дом каждому только что созданному аккаунту.

        Args:
            events: Факты, записанные агрегатами.
        """
        registered = [event for event in events if isinstance(event, UserRegistered)]
        for event in registered:
            await self._provision(event.user_id)

    async def _provision(self, user_id: UserId) -> None:
        async with self._home_uow() as uow:
            devices = [template.build(user_id) for template in STARTER_DEVICES]
            for device in devices:
                await uow.devices.add(device)
            await uow.automation.save(AutomationSettings.create(user_id))
            await uow.preferences.save(UserPreferences.create(user_id))
            await uow.dashboard.save(
                DashboardState.starter(user_id, tuple(device.id for device in devices))
            )
            await uow.commit()
