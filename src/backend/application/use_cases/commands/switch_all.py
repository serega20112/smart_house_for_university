"""Переключить все устройства, которые это умеют."""

from __future__ import annotations

from backend.application.dto.language.clarification_reason import ClarificationReason
from backend.application.dto.language.command_understanding import CommandUnderstanding
from backend.application.dto.language.intent import Intent
from backend.application.errors import CommandNotUnderstoodError
from backend.application.interface.unit_of_work.home import HomeUnitOfWorkFactory
from backend.application.services.device_control import DeviceControlService
from backend.application.use_cases.commands.result import CommandReply
from backend.domain.identifiers import UserId
from backend.domain.value_objects.devices.capability import Capability


class SwitchAllDevicesCommandUseCase:
    """Выполняет «включи всё» и «потуши всё»."""

    def __init__(
        self,
        home_uow: HomeUnitOfWorkFactory,
        control: DeviceControlService,
    ) -> None:
        """Собирает use case переключения всего дома.

        Args:
            home_uow: Граница транзакции над конфигурацией дома.
            control: Сервис, доводящий способность до железа.
        """
        self._home_uow = home_uow
        self._control = control

    @property
    def intent(self) -> Intent:
        """Намерение, которое закрывает этот сценарий."""
        return Intent.SWITCH_ALL

    async def execute(self, user_id: UserId, parsed: CommandUnderstanding) -> CommandReply:
        """Переключает каждое устройство, поддерживающее названную способность.

        Args:
            user_id: Владелец, для которого выполняется команда.
            parsed: Что конвейер понял из фразы.

        Returns:
            CommandReply: Устройства, которых коснулось переключение.

        Raises:
            CommandNotUnderstoodError: Когда фраза не называет направление.
        """
        capability = parsed.capability
        if capability not in (Capability.ON, Capability.OFF):
            raise CommandNotUnderstoodError(ClarificationReason.MISSING_CAPABILITY)
        async with self._home_uow() as uow:
            devices = list(await uow.devices.list_all(user_id))
        report = await self._control.apply_to_all(user_id, devices, capability)
        return CommandReply(
            intent=self.intent,
            answer="",
            details={"devices": [view.name for view in report.devices]},
        )
