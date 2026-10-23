"""Мапперы раскладки дашборда и его виджетов."""

from __future__ import annotations

from uuid import uuid4

from backend.domain.aggregates.dashboard.dashboard_state import DashboardState
from backend.domain.identifiers import DeviceId, UserId
from backend.domain.value_objects.personalization.dashboard_widget import DashboardWidget
from backend.domain.value_objects.personalization.widget_kind import WidgetKind
from backend.infrastructure.database.tables import (
    DashboardRow,
    DashboardWidgetRow,
)


def dashboard_to_row(dashboard: DashboardState) -> DashboardRow:
    """Build the row marking that an account has a layout.

    Args:
        dashboard: Layout to serialize.

    Returns:
        DashboardRow: New row describing the owner of the layout.
    """
    return DashboardRow(user_id=dashboard.user_id.value)


def widget_rows(dashboard: DashboardState) -> list[DashboardWidgetRow]:
    """Build one row per entry of a dashboard layout.

    A layout entry has no identity of its own in the model, so the store assigns
    one. The render order is stored explicitly instead of being implied by an
    arbitrary primary key order.

    Args:
        dashboard: Layout to serialize.

    Returns:
        list[DashboardWidgetRow]: Rows in render order.
    """
    return [
        DashboardWidgetRow(
            id=uuid4(),
            user_id=dashboard.user_id.value,
            position=position,
            kind=widget.kind.value,
            device_id=None if widget.device_id is None else widget.device_id.value,
            title=widget.title,
        )
        for position, widget in enumerate(dashboard.widgets)
    ]


def dashboard_from_row(row: DashboardRow, widgets: list[DashboardWidgetRow]) -> DashboardState:
    """Build the layout a row and its widget rows describe.

    An entry whose device was deleted arrives without one. Such an entry cannot be
    drawn, so it is left out of the layout instead of being handed to the
    aggregate, which would refuse the whole layout over one dead reference.

    Args:
        row: Row identifying the owner of the layout.
        widgets: Widget rows belonging to that owner.

    Returns:
        DashboardState: Restored layout.
    """
    restored: list[DashboardWidget] = []
    for entry in sorted(widgets, key=lambda widget: widget.position):
        widget = widget_from_row(entry)
        if widget is not None:
            restored.append(widget)
    return DashboardState(user_id=UserId.parse(row.user_id), widgets=tuple(restored))


def widget_from_row(row: DashboardWidgetRow) -> DashboardWidget | None:
    """Build one layout entry, or None when it can no longer be drawn.

    Args:
        row: Row to deserialize.

    Returns:
        DashboardWidget | None: Restored entry, or None when the device it
        referenced is gone.
    """
    kind = WidgetKind.parse(row.kind)
    device_id = None if row.device_id is None else DeviceId.parse(row.device_id)
    if kind is WidgetKind.DEVICE and device_id is None:
        return None
    return DashboardWidget(kind=kind, device_id=device_id, title=row.title)
