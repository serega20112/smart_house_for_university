"""
Настройки интерфейса одного аккаунта.

Проекция, а не граница согласованности: за ней стоят только значения —
единица, тема и язык, каждое своим файлом в `value_objects.personalization`.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Self

from backend.domain.identifiers import UserId
from backend.domain.value_objects.personalization.interface_language import InterfaceLanguage
from backend.domain.value_objects.personalization.temperature_unit import TemperatureUnit
from backend.domain.value_objects.personalization.theme import Theme


@dataclass(frozen=True, slots=True)
class UserPreferences:
    """Настройки проекции одного аккаунта.

    Attributes:
        user_id: Владелец настроек.
        temperature_unit: Единица, в которой показывают климат.
        theme: Визуальная тема.
        language: Язык интерфейса.
        show_command_chat: Показывать ли чат команд на главном экране.
    """

    user_id: UserId
    temperature_unit: TemperatureUnit = TemperatureUnit.CELSIUS
    theme: Theme = Theme.DARK
    language: InterfaceLanguage = InterfaceLanguage.RUSSIAN
    show_command_chat: bool = True

    def updated(
        self,
        *,
        temperature_unit: TemperatureUnit | None = None,
        theme: Theme | None = None,
        language: InterfaceLanguage | None = None,
        show_command_chat: bool | None = None,
    ) -> Self:
        """Возвращает настройки с изменёнными указанными полями.

        Каждое поле необязательное, а None означает «оставить»: частичное изменение
        не должно пересобирать весь объект из бесформенного словаря.

        Args:
            temperature_unit: Новая единица или None оставить нынешнюю.
            theme: Новая тема или None оставить нынешнюю.
            language: Новый язык или None оставить нынешний.
            show_command_chat: Новый признак показа или None оставить нынешний.

        Returns:
            Self: Изменённые настройки.
        """
        return UserPreferences(
            user_id=self.user_id,
            temperature_unit=self.temperature_unit
            if temperature_unit is None
            else temperature_unit,
            theme=self.theme if theme is None else theme,
            language=self.language if language is None else language,
            show_command_chat=(
                self.show_command_chat if show_command_chat is None else show_command_chat
            ),
        )

    @classmethod
    def create(cls, user_id: UserId) -> Self:
        """Строит настройки, с которыми начинает свежий аккаунт.

        Args:
            user_id: Владелец настроек.

        Returns:
            Self: Настройки по умолчанию.
        """
        return cls(user_id=user_id)
