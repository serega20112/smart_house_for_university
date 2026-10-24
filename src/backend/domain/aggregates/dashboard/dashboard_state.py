"""Персональная раскладка главного экрана.

Дашборд — данные, а не разметка: он называет, какой готовый компонент нарисовать,
каким устройством его питать и в каком порядке. Именно это превращает одну сборку
интерфейса в персональную проекцию приложения для каждого аккаунта.

Агрегат владеет своими границами и правилом «виджет указывает только на своё
устройство», поэтому сценарий приложения не может сохранить раскладку, которую
интерфейс не в силах нарисовать.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Self

from backend.domain.exceptions import DashboardAccessDeniedError, InvalidDashboardLayoutError
from backend.domain.identifiers import DeviceId, UserId
from backend.domain.value_objects.personalization.dashboard_widget import DashboardWidget
from backend.domain.value_objects.personalization.widget_kind import WidgetKind

MAX_WIDGETS = 40


@dataclass(frozen=True, slots=True)
class DashboardState:
    """Упорядоченный список карточек одного аккаунта.

    Attributes:
        user_id: Владелец раскладки.
        widgets: Карточки в порядке вывода.
    """

    user_id: UserId
    widgets: tuple[DashboardWidget, ...] = ()

    def __post_init__(self) -> None:
        """Проверяет число карточек.

        Raises:
            InvalidDashboardLayoutError: Когда раскладка несёт слишком много карточек.
        """
        if len(self.widgets) > MAX_WIDGETS:
            raise InvalidDashboardLayoutError(f"at most {MAX_WIDGETS} widgets are allowed")

    def rearranged(
        self,
        widgets: tuple[DashboardWidget, ...],
        owned_device_ids: frozenset[DeviceId],
    ) -> Self:
        """Возвращает раскладку, переставленную на новый список карточек.

        Проверка владельца живёт здесь, потому что это неизменяемое условие
        раскладки: дашборд не имеет права ссылаться на устройство чужого аккаунта.

        Args:
            widgets: Новые карточки в желаемом порядке.
            owned_device_ids: Устройства, которыми аккаунт действительно владеет.

        Returns:
            Self: Обновлённая раскладка.

        Raises:
            DashboardAccessDeniedError: Когда карточка указывает на чужое устройство.
            InvalidDashboardLayoutError: Когда список сам нарушает правило.
        """
        for widget in widgets:
            if widget.device_id is not None and widget.device_id not in owned_device_ids:
                raise DashboardAccessDeniedError(str(widget.device_id))
        return DashboardState(user_id=self.user_id, widgets=widgets)

    @classmethod
    def starter(cls, user_id: UserId, device_ids: tuple[DeviceId, ...]) -> Self:
        """Строит раскладку, с которой начинает свежезарегистрированный аккаунт.

        Args:
            user_id: Владелец раскладки.
            device_ids: Идентификаторы устройств, созданных вместе с аккаунтом.

        Returns:
            Self: Раскладка с карточкой климата, чатом команд и по одной карточке
            на каждое настроенное устройство.
        """
        widgets: list[DashboardWidget] = [
            DashboardWidget(kind=WidgetKind.CLIMATE),
            DashboardWidget(kind=WidgetKind.COMMAND),
        ]
        widgets.extend(DashboardWidget(kind=WidgetKind.DEVICE, device_id=id_) for id_ in device_ids)
        return cls(user_id=user_id, widgets=tuple(widgets))
