"""Personalized dashboard layout.

The dashboard is data, not markup: it names which generic component has to be
rendered, which device feeds it and in which order. That is what turns one
frontend build into a personalized projection of the application for every
account.

The aggregate owns its limits and the rule that a widget may only point at a
device the account owns, so a use case cannot store a layout the interface is
unable to draw.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Self

from backend.domain.exceptions import DashboardAccessDeniedError, InvalidDashboardLayoutError
from backend.domain.identifiers import DeviceId, UserId
from backend.domain.personalization.dashboard_widget import DashboardWidget
from backend.domain.personalization.widget_kind import WidgetKind

MAX_WIDGETS = 40


@dataclass(frozen=True, slots=True)
class DashboardState:
    """The ordered widget list of one account.

    Args:
        user_id: Owner of the layout.
        widgets: Widgets in the order they have to be rendered.

    Returns:
        None.
    """

    user_id: UserId
    widgets: tuple[DashboardWidget, ...] = ()

    def __post_init__(self) -> None:
        """Validate the number of widgets.

        Returns:
            None.

        Raises:
            InvalidDashboardLayoutError: When the layout carries too many widgets.
        """
        if len(self.widgets) > MAX_WIDGETS:
            raise InvalidDashboardLayoutError(f"at most {MAX_WIDGETS} widgets are allowed")

    def rearranged(
        self,
        widgets: tuple[DashboardWidget, ...],
        owned_device_ids: frozenset[DeviceId],
    ) -> Self:
        """Return the layout reordered to a new widget list.

        The ownership check lives here because it is an invariant of the layout:
        a dashboard may never reference a device of another account.

        Args:
            widgets: New widgets in the desired order.
            owned_device_ids: Devices the account actually owns.

        Returns:
            Self: Updated layout.

        Raises:
            DashboardAccessDeniedError: When a widget points at a foreign device.
            InvalidDashboardLayoutError: When the list itself breaks a rule.
        """
        for widget in widgets:
            if widget.device_id is not None and widget.device_id not in owned_device_ids:
                raise DashboardAccessDeniedError(str(widget.device_id))
        return DashboardState(user_id=self.user_id, widgets=widgets)

    @classmethod
    def starter(
        cls, user_id: UserId, device_ids: tuple[DeviceId, ...]
    ) -> Self:
        """Build the layout a freshly registered account starts with.

        Args:
            user_id: Owner of the layout.
            device_ids: Identifiers of the devices created with the account.

        Returns:
            Self: Layout showing the climate card, the command chat and one card
            per configured device.
        """
        widgets: list[DashboardWidget] = [
            DashboardWidget(kind=WidgetKind.CLIMATE),
            DashboardWidget(kind=WidgetKind.COMMAND),
        ]
        widgets.extend(DashboardWidget(kind=WidgetKind.DEVICE, device_id=id_) for id_ in device_ids)
        return cls(user_id=user_id, widgets=tuple(widgets))
