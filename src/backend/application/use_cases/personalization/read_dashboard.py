"""Прочитать раскладку главного экрана одного аккаунта.

Сохранённая раскладка задаёт порядок и личные заголовки карточек, а набор карточек
устройств сверяется с тем, чем аккаунт владеет сейчас: заведённое устройство
появляется на экране само, удалённое уходит. Сверка живёт здесь, потому что
устройства и раскладка меняются разными сценариями, и только чтение видит оба
набора одновременно.
"""

from __future__ import annotations

from backend.application.dto.views.dashboard_view import DashboardView
from backend.application.interfaces.unit_of_work.home import HomeUnitOfWorkFactory
from backend.domain.aggregates.dashboard.dashboard_state import DashboardState
from backend.domain.identifiers import UserId


class ReadDashboardUseCase:
    """Отдаёт упорядоченный список виджетов, который человек собрал себе сам."""

    def __init__(self, home_uow: HomeUnitOfWorkFactory) -> None:
        """Собирает чтение раскладки.

        Args:
            home_uow: Фабрика транзакций над настройкой дома.
        """
        self._home_uow = home_uow

    async def execute(self, user_id: UserId) -> DashboardView:
        """Возвращает раскладку аккаунта, покрывающую его устройства.

        Раскладки может не быть вовсе: тогда её начинают со стандартного набора
        карточек, а не с пустого экрана. Сохранённый порядок не переписывается —
        здесь только читают, поэтому проекция остаётся дешёвой.

        Args:
            user_id: Владелец раскладки.

        Returns:
            DashboardView: Виджеты в порядке вывода.
        """
        async with self._home_uow() as uow:
            stored = await uow.dashboard.get(user_id)
            devices = await uow.devices.list_all(user_id)
        layout = stored if stored is not None else DashboardState.starter(user_id, ())
        device_ids = tuple(device.id for device in devices)
        return DashboardView(widgets=layout.covering(device_ids).widgets)
