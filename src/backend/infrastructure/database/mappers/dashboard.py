"""Мапперы раскладки дашборда и его виджетов."""

from __future__ import annotations

from uuid import uuid4

from backend.domain.aggregates.dashboard.dashboard_state import DashboardState
from backend.domain.entities.personalization.dashboard_widget import DashboardWidget
from backend.domain.identifiers import DeviceId, UserId
from backend.domain.value_objects.personalization.widget_kind import WidgetKind
from backend.infrastructure.database.models import (
    DashboardModel,
    DashboardWidgetModel,
)


def dashboard_to_row(dashboard: DashboardState) -> DashboardModel:
    """Строит строку, отмечающую, что у аккаунта есть раскладка.

    Args:
        dashboard: Раскладка для сериализации.

    Returns:
        DashboardModel: Новая строка, описывающая владельца раскладки.
    """
    return DashboardModel(user_id=dashboard.user_id.value)


def widget_rows(dashboard: DashboardState) -> list[DashboardWidgetModel]:
    """Строит по строке на каждую карточку раскладки главного экрана.

    Своей идентичности у карточки в модели нет, поэтому хранилище выдаёт её само. Порядок
    вывода записывают явно, а не выводят из произвольного порядка первичного ключа.

    Args:
        dashboard: Раскладка для сериализации.

    Returns:
        list[DashboardWidgetModel]: Строки в порядке вывода.
    """
    return [
        DashboardWidgetModel(
            id=uuid4(),
            user_id=dashboard.user_id.value,
            position=position,
            kind=widget.kind.value,
            device_id=None if widget.device_id is None else widget.device_id.value,
            title=widget.title,
        )
        for position, widget in enumerate(dashboard.widgets)
    ]


def dashboard_from_row(row: DashboardModel, widgets: list[DashboardWidgetModel]) -> DashboardState:
    """Строит раскладку, описанную её строкой и строками карточек.

    Карточка, чьё устройство удалили, приходит без него. Нарисовать такую нельзя, поэтому
    её из раскладки убирают, а не несут агрегату, который отверг бы всю раскладку из-за
    одной мёртвой ссылки.

    Args:
        row: Строка, называющая владельца раскладки.
        widgets: Строки карточек этого владельца.

    Returns:
        DashboardState: Восстановленная раскладка.
    """
    restored: list[DashboardWidget] = []
    for entry in sorted(widgets, key=lambda widget: widget.position):
        widget = widget_from_row(entry)
        if widget is not None:
            restored.append(widget)
    return DashboardState(user_id=UserId.parse(row.user_id), widgets=tuple(restored))


def widget_from_row(row: DashboardWidgetModel) -> DashboardWidget | None:
    """Строит одну карточку раскладки или None, когда её больше нельзя нарисовать.

    Args:
        row: Строка для десериализации.

    Returns:
        DashboardWidget | None: Восстановленная карточка или None, когда устройство,
        на которое она указывала, исчезло.
    """
    kind = WidgetKind.parse(row.kind)
    device_id = None if row.device_id is None else DeviceId.parse(row.device_id)
    if kind is WidgetKind.DEVICE and device_id is None:
        return None
    return DashboardWidget(kind=kind, device_id=device_id, title=row.title)
