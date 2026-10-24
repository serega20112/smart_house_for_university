from __future__ import annotations

from backend.domain.aggregates.dashboard.dashboard_state import MAX_WIDGETS, DashboardState
from backend.domain.entities.personalization.dashboard_widget import DashboardWidget
from backend.domain.identifiers import DeviceId, UserId
from backend.domain.value_objects.personalization.widget_kind import WidgetKind

OWNER_UUID = "550e8400-e29b-41d4-a716-446655440000"


def make_dashboard() -> DashboardState:
    return DashboardState(
        user_id=UserId.parse(OWNER_UUID),
        widgets=(
            DashboardWidget(kind=WidgetKind.CLIMATE),
            DashboardWidget(kind=WidgetKind.COMMAND),
        ),
    )


def test_dashboard_state_covering_appends_a_card_for_every_configured_device() -> None:
    layout = make_dashboard()
    light = DeviceId.generate()
    heater = DeviceId.generate()

    covered = layout.covering((light, heater))

    assert [widget.kind for widget in covered.widgets] == [
        WidgetKind.CLIMATE,
        WidgetKind.COMMAND,
        WidgetKind.DEVICE,
        WidgetKind.DEVICE,
    ]
    assert [widget.device_id for widget in covered.widgets[-2:]] == [light, heater]


def test_dashboard_state_covering_keeps_the_stored_order_and_titles() -> None:
    light = DeviceId.generate()
    heater = DeviceId.generate()
    layout = DashboardState(
        user_id=UserId.parse(OWNER_UUID),
        widgets=(
            DashboardWidget(kind=WidgetKind.DEVICE, device_id=heater, title="Коридор"),
            DashboardWidget(kind=WidgetKind.CLIMATE),
            DashboardWidget(kind=WidgetKind.DEVICE, device_id=light, title="Кухня"),
        ),
    )

    covered = layout.covering((light, heater))

    assert covered.widgets == layout.widgets


def test_dashboard_state_covering_drops_the_card_of_a_deleted_device() -> None:
    light = DeviceId.generate()
    deleted = DeviceId.generate()
    layout = DashboardState(
        user_id=UserId.parse(OWNER_UUID),
        widgets=(DashboardWidget(kind=WidgetKind.DEVICE, device_id=deleted),),
    )

    covered = layout.covering((light,))

    assert [widget.device_id for widget in covered.widgets] == [light]


def test_dashboard_state_covering_a_second_time_changes_nothing() -> None:
    light = DeviceId.generate()
    once = make_dashboard().covering((light,))

    assert once.covering((light,)) == once


def test_dashboard_state_covering_stops_at_the_widget_limit() -> None:
    devices = tuple(DeviceId.generate() for _ in range(MAX_WIDGETS))
    layout = DashboardState(user_id=UserId.parse(OWNER_UUID))

    covered = layout.covering(devices)

    assert len(covered.widgets) == MAX_WIDGETS
