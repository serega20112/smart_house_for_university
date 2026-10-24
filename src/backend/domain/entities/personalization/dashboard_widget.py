"""
Одна карточка раскладки главного экрана.

Карточка — часть раскладки своего аккаунта и живёт только внутри неё: вне
DashboardState она не значит ничего.
"""

from __future__ import annotations

from dataclasses import dataclass

from backend.domain.exceptions import InvalidDashboardLayoutError
from backend.domain.identifiers import DeviceId
from backend.domain.value_objects.personalization.widget_kind import WidgetKind

MAX_TITLE_LENGTH = 60


@dataclass(frozen=True, slots=True)
class DashboardWidget:
    """Компонент для вывода, необязательно питаемый одним устройством.

    Attributes:
        kind: Какой из готовых компонентов рисовать.
        device_id: Устройство, которым его питают, или None для общего.
        title: Личный заголовок поверх значения по умолчанию.

    Raises:
        InvalidDashboardLayoutError: Когда заголовок длиннее разрешённого.
    """

    kind: WidgetKind
    device_id: DeviceId | None = None
    title: str | None = None

    def __post_init__(self) -> None:
        """Проверяет карточку саму по себе.

        Raises:
            InvalidDashboardLayoutError: Когда заголовок пустой или слишком длинный,
            или когда карточке устройства не назвали устройство.
        """
        if self.title is not None:
            trimmed = self.title.strip()
            if not trimmed or len(trimmed) > MAX_TITLE_LENGTH:
                raise InvalidDashboardLayoutError("a widget title is empty or too long")
            object.__setattr__(self, "title", trimmed)
        if self.kind is WidgetKind.DEVICE and self.device_id is None:
            raise InvalidDashboardLayoutError("a device widget must name a device")

    def rename(self, title: str | None) -> DashboardWidget:
        """Возвращает ту же карточку под другим заголовком.

        Args:
            title: Новый личный заголовок или None ради значения по умолчанию.

        Returns:
            DashboardWidget: Карточка с новым заголовком.
        """
        return DashboardWidget(kind=self.kind, device_id=self.device_id, title=title)
