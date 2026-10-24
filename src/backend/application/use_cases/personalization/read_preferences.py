"""Прочитать настройки интерфейса одного аккаунта."""

from __future__ import annotations

from backend.application.interfaces.unit_of_work.home import HomeUnitOfWorkFactory
from backend.domain.entities.personalization.user_preferences import UserPreferences
from backend.domain.identifiers import UserId
from backend.domain.value_objects.personalization.preferences_view import PreferencesView


class ReadPreferencesUseCase:
    """Отдаёт настройки того, как человеку рисовать интерфейс."""

    def __init__(self, home_uow: HomeUnitOfWorkFactory) -> None:
        """Собирает чтение настроек.

        Args:
            home_uow: Фабрика транзакций над настройкой дома.
        """
        self._home_uow = home_uow

    async def execute(self, user_id: UserId) -> PreferencesView:
        """Возвращает настройки интерфейса аккаунта.

        Аккаунт, зарегистрированный до того, как настройки стали отдельной
        строкой, получает значения по умолчанию: экран обязан показать что-то
        вменяемое вместо отказа.

        Args:
            user_id: Владелец настроек.

        Returns:
            PreferencesView: Настройки такие, какие сохранены.
        """
        async with self._home_uow() as uow:
            stored = await uow.preferences.get(user_id)
        preferences = stored if stored is not None else UserPreferences.create(user_id)
        return PreferencesView(
            temperature_unit=preferences.temperature_unit,
            theme=preferences.theme,
            language=preferences.language,
            show_command_chat=preferences.show_command_chat,
        )
