"""Реакции на факты, которые записывает модель.

Правила «ручное действие держит автоматику в стороне» и «закончивший сценарий возвращает
устройства» записаны здесь как реакции на то, что записал агрегат, а не строками в конце
каждого сценария приложения. Сценарию, переключающему устройство, поэтому не нужно ничего
помнить, а новая точка входа в систему получает это поведение даром.
"""

from __future__ import annotations

from datetime import timedelta

from backend.application.interface.services.clock import Clock
from backend.application.interface.services.home_state_store import HomeStateStore
from backend.domain.events import DeviceCapabilityApplied
from backend.domain.identifiers import UserId


class ManualOverrideReaction:
    """Держит автоматику в стороне на время после ручного вмешательства."""

    def __init__(self, state_store: HomeStateStore, clock: Clock, override_minutes: int) -> None:
        """Инициализирует реакцию.

        Args:
            state_store: Надёжный дом изменчивого состояния.
            clock: Источник текущего времени.
            override_minutes: Сколько ручное действие держит автоматику в стороне.
        """
        self._state_store = state_store
        self._clock = clock
        self._override_minutes = override_minutes

    async def __call__(self, events: tuple[object, ...]) -> None:
        """Реагирует на записанные факты.

        Args:
            events: Факты, записанные агрегатом.
        """
        manual = [
            event for event in events if isinstance(event, DeviceCapabilityApplied) and event.manual
        ]
        if not manual:
            return
        by_home: dict[UserId, object] = {}
        for event in manual:
            by_home[event.user_id] = None
        for user_id in by_home:
            until = self._clock.now() + timedelta(minutes=self._override_minutes)
            await self._state_store.set_override_until(user_id, until)
