"""Прочитать раскладку главного экрана одного аккаунта."""

from __future__ import annotations

from backend.application.interface.unit_of_work.home import HomeUnitOfWorkFactory
from backend.domain.identifiers import UserId
from backend.domain.value_objects.personalization.dashboard_view import DashboardView


class ReadDashboardUseCase:
    """Отдаёт упорядоченный список виджетов, который человек собрал себе сам."""

    def __init__(self, home_uow: HomeUnitOfWorkFactory) -> None:
        """Собирает чтение раскладки.

        Args:
            home_uow: Фабрика транзакций над настройкой дома.
        """
        self._home_uow = home_uow

    async def execute(self, user_id: UserId) -> DashboardView:
        """Возвращает раскладку аккаунта.

        Пустой список — законное значение: экран без виджетов отличается от экрана,
        которого ещё не было, и придумывать за человека его панель здесь не начинают.

        Args:
            user_id: Владелец раскладки.

        Returns:
            DashboardView: Виджеты в порядке вывода.
        """
        async with self._home_uow() as uow:
            stored = await uow.dashboard.get(user_id)
        if stored is None:
            return DashboardView(widgets=())
        return DashboardView(widgets=stored.widgets)
