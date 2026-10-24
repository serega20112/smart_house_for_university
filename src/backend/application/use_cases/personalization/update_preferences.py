"""Изменить настройки интерфейса одного аккаунта."""

from __future__ import annotations

from backend.application.dto.personalization.preferences_patch import PreferencesPatch
from backend.application.dto.views.preferences_view import PreferencesView
from backend.application.interfaces.unit_of_work.home import HomeUnitOfWorkFactory
from backend.domain.entities.personalization.user_preferences import UserPreferences
from backend.domain.identifiers import UserId


class UpdatePreferencesUseCase:
    """Применяет частичное изменение того, как рисовать интерфейс."""

    def __init__(self, home_uow: HomeUnitOfWorkFactory) -> None:
        """Собирает изменение настроек.

        Args:
            home_uow: Фабрика транзакций над настройкой дома.
        """
        self._home_uow = home_uow

    async def execute(self, user_id: UserId, patch: PreferencesPatch) -> PreferencesView:
        """Меняет заданные поля и оставляет остальные.

        Args:
            user_id: Владелец настроек.
            patch: Поля, которые нужно изменить.

        Returns:
            PreferencesView: Настройки такие, какими они стали.
        """
        async with self._home_uow() as uow:
            stored = await uow.preferences.get(user_id)
            preferences = stored if stored is not None else UserPreferences.create(user_id)
            preferences = preferences.updated(
                temperature_unit=patch.temperature_unit,
                theme=patch.theme,
                language=patch.language,
                show_command_chat=patch.show_command_chat,
            )
            await uow.preferences.save(preferences)
            await uow.commit()
        return PreferencesView(
            temperature_unit=preferences.temperature_unit,
            theme=preferences.theme,
            language=preferences.language,
            show_command_chat=preferences.show_command_chat,
        )
