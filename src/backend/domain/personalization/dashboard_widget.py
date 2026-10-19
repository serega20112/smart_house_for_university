"""One entry of a dashboard layout."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Self

from backend.domain.exceptions import InvalidDashboardLayoutError
from backend.domain.identifiers import DeviceId
from backend.domain.personalization.widget_kind import WidgetKind

MAX_TITLE_LENGTH = 60


@dataclass(frozen=True, slots=True)
class DashboardWidget:
    """A component to render, optionally fed by one device.

    Args:
        kind: Which generic component to draw.
        device_id: Device feeding the component, or None for a global one.
        title: Personal title overriding the component default.

    Returns:
        None.

    Raises:
        InvalidDashboardLayoutError: When the title is longer than allowed.
    """

    kind: WidgetKind
    device_id: DeviceId | None = None
    title: str | None = None

    def __post_init__(self) -> None:
        """Validate the widget on its own.

        Args:
            None.

        Returns:
            None.

        Raises:
            InvalidDashboardLayoutError: When the title is too long or a widget
            that needs a device does not name one.
        """
        if self.title is not None:
            trimmed = self.title.strip()
            if not trimmed or len(trimmed) > MAX_TITLE_LENGTH:
                raise InvalidDashboardLayoutError("a widget title is empty or too long")
            object.__setattr__(self, "title", trimmed)
        if self.kind is WidgetKind.DEVICE and self.device_id is None:
            raise InvalidDashboardLayoutError("a device widget must name a device")

    def rename(self, title: str | None) -> Self:
        """Return the same widget under a different title.

        Args:
            title: New personal title or None to fall back to the default.

        Returns:
            Self: Widget with the new title.
        """
        return DashboardWidget(kind=self.kind, device_id=self.device_id, title=title)
