"""Меняет сеть, которую предписано использовать плате.

Владелец меняет сеть платы в интерфейсе, а бэкенд передаёт новые настройки плате
через уже открытый сокет. Плата пишет их в собственную флеш-память и
переподключается, поэтому второй раз толкать настройки не нужно: с этого момента
они живут в чипе.

Копию настроек держит и бэкенд: именно её показывает интерфейс, её же плата
просит снова, когда настроенная самостоятельно плата сообщает сеть, которую никто
не выбирал, и её же получает плата, вернувшаяся после неприменимого изменения.
"""

from __future__ import annotations

from backend.application.dto.boards.set_network_command import SetNetworkCommand
from backend.application.errors import BoardNotFoundError
from backend.application.interfaces.services.boards.board_gateway import BoardGateway
from backend.application.interfaces.services.system.clock import Clock
from backend.application.interfaces.unit_of_work.board_onboarding import (
    BoardOnboardingUnitOfWorkFactory,
)
from backend.domain.entities.boards.board_network import BoardNetwork
from backend.domain.identifiers import EspDeviceId, UserId
from backend.domain.value_objects.boards.board_network_view import BoardNetworkView
from backend.domain.value_objects.boards.network_profile import NetworkProfile


class ConfigureBoardNetworkUseCase:
    """Меняет сеть платы и сообщает её плате."""

    def __init__(
        self,
        onboarding_uow: BoardOnboardingUnitOfWorkFactory,
        boards: BoardGateway,
        clock: Clock,
    ) -> None:
        """Собирает сценарий смены сети.

        Args:
            onboarding_uow: Граница транзакции над платами.
            boards: Шлюз, команды которого доходят до плат.
            clock: Источник текущего момента.
        """
        self._uow = onboarding_uow
        self._boards = boards
        self._clock = clock

    async def execute(
        self, user_id: UserId, board_id: EspDeviceId, command: SetNetworkCommand
    ) -> BoardNetworkView:
        """Сохраняет сеть платы и передаёт её плате.

        Настройки сохраняются даже когда плата недоступна: плата, настроенная
        самостоятельно, ещё не знает сети бэкенда, и владелец вправе записать
        настройки до того, как плата появится.

        Args:
            user_id: Владелец платы.
            board_id: Идентификатор платы.
            command: Сеть, которую должна использовать плата.

        Returns:
            BoardNetworkView: Сеть такой, какой её видит интерфейс.

        Raises:
            BoardNotFoundError: Когда у аккаунта нет такой платы.
            InvalidNetworkProfileError: Когда настройки неприменимы.
        """
        profile = NetworkProfile(
            ssid=command.ssid,
            password=command.password,
            host=command.host,
            server_port=command.server_port,
            socket_port=command.socket_port,
            socket_path=command.socket_path,
        )
        now = self._clock.now()
        async with self._uow() as uow:
            board = await uow.boards.get(user_id, board_id)
            if board is None:
                raise BoardNotFoundError(board_id)
            await uow.networks.save(
                BoardNetwork(board_id=board_id, user_id=user_id, profile=profile, updated_at=now)
            )
        await self._boards.set_network(user_id, board_id, profile)
        return BoardNetworkView.of(board_id, profile, now)
