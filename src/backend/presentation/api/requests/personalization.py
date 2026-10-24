"""Тела запросов персонализации и перевод их в команды приложения."""

from __future__ import annotations

from pydantic import Field

from backend.application.dto.personalization.dashboard_patch import DashboardPatch
from backend.application.dto.personalization.preferences_patch import PreferencesPatch
from backend.domain.aggregates.preferences.user_preferences import (
    InterfaceLanguage,
    TemperatureUnit,
    Theme,
)
from backend.domain.identifiers import DeviceId
from backend.domain.value_objects.personalization.dashboard_widget import DashboardWidget
from backend.domain.value_objects.personalization.widget_kind import WidgetKind
from backend.presentation.api.base import StrictModel

TITLE_MAX_LENGTH = 60


class PreferencesBody(StrictModel):
    """Частичное изменение настроек интерфейса.

    Единицы, темы и языки задаются строго перечислениями домена: интерфейс не может
    сохранить настройку, которую он не умеет нарисовать.

    Attributes:
        temperature_unit: Новая единица температуры или None.
        theme: Новая тема или None.
        language: Новый язык интерфейса или None.
        show_command_chat: Показывать ли чат команд, либо None.
    """

    temperature_unit: str | None = Field(default=None, pattern="^[CF]$")
    theme: str | None = Field(default=None, pattern="^(dark|light)$")
    language: str | None = Field(default=None, pattern="^(ru|en)$")
    show_command_chat: bool | None = None


class DashboardWidgetBody(StrictModel):
    """Одна карточка главного экрана.

    Attributes:
        type: Какую из готовых карточек рисовать.
        device_id: Устройство, которым её питают, либо None.
        title: Личный заголовок поверх значения по умолчанию.
    """

    type: WidgetKind
    device_id: str | None = None
    title: str | None = Field(default=None, max_length=TITLE_MAX_LENGTH)


class DashboardBody(StrictModel):
    """Новая раскладка главного экрана.

    Attributes:
        widgets: Виджеты в том порядке, в котором их выводить.
    """

    widgets: list[DashboardWidgetBody]


def preferences_patch(body: PreferencesBody) -> PreferencesPatch:
    """Возвращает команду частичного изменения настроек.

    Args:
        body: Поля, которые человек хочет изменить.

    Returns:
        PreferencesPatch: Команда, понятная сценарию приложения.
    """
    return PreferencesPatch(
        temperature_unit=(
            None if body.temperature_unit is None else TemperatureUnit(body.temperature_unit)
        ),
        theme=None if body.theme is None else Theme(body.theme),
        language=None if body.language is None else InterfaceLanguage(body.language),
        show_command_chat=body.show_command_chat,
    )


def dashboard_patch(body: DashboardBody) -> DashboardPatch:
    """Возвращает команду замены раскладки главного экрана.

    Args:
        body: Виджеты в новом порядке.

    Returns:
        DashboardPatch: Команда, понятная сценарию приложения.
    """
    return DashboardPatch(
        widgets=tuple(
            DashboardWidget(
                kind=widget.type,
                device_id=(None if widget.device_id is None else DeviceId.parse(widget.device_id)),
                title=widget.title,
            )
            for widget in body.widgets
        )
    )
