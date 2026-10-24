"""Выполнить способность, названную или выведенную из цели."""

from __future__ import annotations

from backend.application.dto.language.clarification_reason import ClarificationReason
from backend.application.dto.language.command_understanding import CommandUnderstanding
from backend.application.dto.language.intent import Intent
from backend.application.errors import CommandNotUnderstoodError
from backend.application.interfaces.services.state.home_state_store import HomeStateStore
from backend.application.interfaces.unit_of_work.home import HomeUnitOfWorkFactory
from backend.application.services.device_control import DeviceControlService
from backend.application.use_cases.commands.result import CommandReply
from backend.domain.identifiers import UserId
from backend.domain.policies.climate_policy import DemandCalculator
from backend.domain.value_objects.devices.capability import Capability


class RunCapabilityCommandUseCase:
    """Выполняет «тут жарко» и «сделай прохладнее»."""

    def __init__(
        self,
        home_uow: HomeUnitOfWorkFactory,
        control: DeviceControlService,
        state_store: HomeStateStore,
        demands: DemandCalculator,
    ) -> None:
        """Собирает use case выполнения способности.

        Args:
            home_uow: Граница транзакции над конфигурацией дома.
            control: Сервис, доводящий способность до железа.
            state_store: Хранилище изменчивого состояния дома.
            demands: Модель, решающая, какая способность ведёт к цели.
        """
        self._home_uow = home_uow
        self._control = control
        self._state_store = state_store
        self._demands = demands

    @property
    def intent(self) -> Intent:
        """Намерение, которое закрывает этот сценарий."""
        return Intent.RUN_CAPABILITY

    async def execute(self, user_id: UserId, parsed: CommandUnderstanding) -> CommandReply:
        """Выполняет названную способность.

        Фраза, назвавшая цель без направления, разбирается по измеренной
        температуре — это решение модели, а не догадка маршрутизатора.

        Args:
            user_id: Владелец, для которого выполняется команда.
            parsed: Что конвейер понял из фразы.

        Returns:
            CommandReply: Устройство, которым управляли.

        Raises:
            CommandNotUnderstoodError: Когда способность не выводится ни из чего.
        """
        capability = parsed.capability or await self._from_target(user_id, parsed)
        if capability is None:
            raise CommandNotUnderstoodError(ClarificationReason.MISSING_CAPABILITY)
        async with self._home_uow() as uow:
            devices = list(await uow.devices.list_all(user_id))
        view = await self._control.apply_to_first_matching(user_id, devices, capability)
        return CommandReply(
            intent=self.intent,
            answer="",
            details={"device": view.name, "capability": capability.value},
        )

    async def _from_target(
        self, user_id: UserId, parsed: CommandUnderstanding
    ) -> Capability | None:
        if parsed.temperature is None:
            return None
        state = await self._state_store.read(user_id)
        measured = state.reading.temperature
        return self._demands.capability_towards(
            parsed.temperature.celsius, None if measured is None else measured.celsius
        )
