"""Заменить раскладку главного экрана одного аккаунта."""

from __future__ import annotations

from backend.application.dto.personalization.dashboard_patch import DashboardPatch
from backend.application.dto.views.dashboard_view import DashboardView
from backend.application.interfaces.unit_of_work.home import HomeUnitOfWorkFactory
from backend.domain.aggregates.dashboard.dashboard_state import DashboardState
from backend.domain.identifiers import UserId


class UpdateDashboardUseCase:
    """Сохраняет новый порядок виджетов экрана."""

    def __init__(self, home_uow: HomeUnitOfWorkFactory) -> None:
        """Собирает замену раскладки.

        Args:
            home_uow: Фабрика транзакций над настройкой дома.
        """
        self._home_uow = home_uow

    async def execute(self, user_id: UserId, patch: DashboardPatch) -> DashboardView:
        """Заменяет список виджетов целиком.

        Проверка «виджет указывает только на своё устройство» живёт в агрегате, а
        список устройств для неё берётся здесь: без своего дома раскладку построить
        нельзя, и чужой идентификатор даёт отказ, а не пустую карточку.

        Args:
            user_id: Владелец раскладки.
            patch: Виджеты в новом порядке.

        Returns:
            DashboardView: Сохранённая раскладка.
        """
        async with self._home_uow() as uow:
            stored = await uow.dashboard.get(user_id)
            state = stored if stored is not None else DashboardState(user_id=user_id)
            devices = await uow.devices.list_all(user_id)
            state = state.rearranged(patch.widgets, frozenset(device.id for device in devices))
            await uow.dashboard.save(state)
            await uow.commit()
        return DashboardView(widgets=state.widgets)
