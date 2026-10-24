"""Ответы про персональную проекцию: настройки интерфейса и раскладку экрана."""

from __future__ import annotations

from backend.domain.value_objects.personalization.dashboard_view import DashboardView
from backend.domain.value_objects.personalization.preferences_view import PreferencesView
from backend.presentation.api.responses.common import StrictModel


class PreferencesResponse(StrictModel):
    """Настройки интерфейса, которые человек выбрал сам.

    Attributes:
        temperature_unit: Единица, в которой показывают климат.
        theme: Визуальная тема.
        language: Язык интерфейса.
        show_command_chat: Показывать ли чат команд.
    """

    temperature_unit: str
    theme: str
    language: str
    show_command_chat: bool


class DashboardWidgetResponse(StrictModel):
    """Одна карточка главного экрана.

    Attributes:
        type: Какую из готовых карточек рисовать.
        device_id: Устройство, которым её питают, либо None.
        title: Личный заголовок поверх значения по умолчанию.
    """

    type: str
    device_id: str | None
    title: str | None


class DashboardResponse(StrictModel):
    """Раскладка главного экрана одного аккаунта.

    Attributes:
        widgets: Виджеты в порядке вывода.
    """

    widgets: list[DashboardWidgetResponse]


def preferences_of(view: PreferencesView) -> PreferencesResponse:
    """Возвращает тело настроек интерфейса.

    Args:
        view: Настройки таким, каким их видит прикладной слой.

    Returns:
        PreferencesResponse: Тело настроек.
    """
    return PreferencesResponse(
        temperature_unit=view.temperature_unit.value,
        theme=view.theme.value,
        language=view.language.value,
        show_command_chat=view.show_command_chat,
    )


def dashboard_of(view: DashboardView) -> DashboardResponse:
    """Возвращает тело раскладки экрана.

    Args:
        view: Раскладка таким, каким её видит прикладной слой.

    Returns:
        DashboardResponse: Тело раскладки.
    """
    return DashboardResponse(
        widgets=[
            DashboardWidgetResponse(
                type=widget.kind.value,
                device_id=None if widget.device_id is None else str(widget.device_id),
                title=widget.title,
            )
            for widget in view.widgets
        ]
    )
