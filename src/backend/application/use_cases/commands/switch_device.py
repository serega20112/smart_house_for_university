"""Переключить одно устройство, названное человеком."""

from __future__ import annotations

from collections.abc import Sequence

from backend.application.dto.language.clarification_reason import ClarificationReason
from backend.application.dto.language.command_understanding import CommandUnderstanding
from backend.application.dto.language.intent import Intent
from backend.application.errors import CommandNotUnderstoodError
from backend.application.interfaces.unit_of_work.home import HomeUnitOfWorkFactory
from backend.application.services.device_control import DeviceControlService
from backend.application.use_cases.commands.result import CommandReply
from backend.domain.aggregates.device.device import Device
from backend.domain.identifiers import UserId
from backend.domain.policies.device_selector import DeviceSelector
from backend.domain.value_objects.devices.capability import Capability


class SwitchDeviceCommandUseCase:
    """Выполняет «включи свет» и «выключи кондиционер»."""

    def __init__(
        self,
        home_uow: HomeUnitOfWorkFactory,
        control: DeviceControlService,
        selector: DeviceSelector,
    ) -> None:
        """Собирает use case переключения одного устройства.

        Args:
            home_uow: Граница транзакции над конфигурацией дома.
            control: Сервис, доводящий способность до железа.
            selector: Находит устройство по названному имени или виду.
        """
        self._home_uow = home_uow
        self._control = control
        self._selector = selector

    @property
    def intent(self) -> Intent:
        """Намерение, которое закрывает этот сценарий."""
        return Intent.SWITCH_DEVICE

    async def execute(self, user_id: UserId, parsed: CommandUnderstanding) -> CommandReply:
        """Переключает устройство, на которое указывает фраза.

        Направление берётся из самой фразы: «выключи» и «включи» различает
        конвейер понимания, а не выбор сценария в шине.

        Args:
            user_id: Владелец, для которого выполняется команда.
            parsed: Что конвейер понял из фразы.

        Returns:
            CommandReply: Устройство и состояние, которого оно достигло.

        Raises:
            CommandNotUnderstoodError: Когда фраза не называет известное устройство
                или не говорит, в какую сторону переключать.
        """
        capability = self._direction(parsed)
        devices = await self._devices(user_id)
        device = self._resolve(devices, parsed)
        if device is None:
            raise CommandNotUnderstoodError(
                ClarificationReason.UNKNOWN_DEVICE, device=parsed.device_name
            )
        view = await self._control.apply_to_device(user_id, device.id, capability)
        return CommandReply(
            intent=self.intent,
            answer="",
            details={"device": view.name, "status": view.status.value},
        )

    @staticmethod
    def _direction(parsed: CommandUnderstanding) -> Capability:
        if parsed.capability in (Capability.ON, Capability.OFF):
            return parsed.capability
        raise CommandNotUnderstoodError(ClarificationReason.MISSING_CAPABILITY)

    async def _devices(self, user_id: UserId) -> Sequence[Device]:
        async with self._home_uow() as uow:
            return list(await uow.devices.list_all(user_id))

    def _resolve(self, devices: Sequence[Device], parsed: CommandUnderstanding) -> Device | None:
        if parsed.device_name:
            return self._selector.by_name(devices, parsed.device_name)
        if parsed.device_kinds:
            candidates = self._selector.of_kind(devices, parsed.device_kinds)
            return candidates[0] if candidates else None
        return None
