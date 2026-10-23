"""Маршруты сети платы.

Владелец меняет сеть платы в интерфейсе, и значения уходят плате через уже
открытый сокет. Плата пишет их в собственную флеш-память и переподключается,
поэтому вводить их в плату второй раз не нужно.

Пароль сети — секрет: он приходит в запросе, доходит до платы и там остаётся. В
ответе его нет, поэтому интерфейс не покажет его даже случайно.
"""

from __future__ import annotations

from dishka import FromDishka
from dishka.integrations.fastapi import DishkaRoute
from fastapi import APIRouter

from backend.application.errors import BoardNotFoundError
from backend.application.use_cases.boards.configure_board_network import (
    ConfigureBoardNetworkUseCase,
)
from backend.application.use_cases.boards.read_board_network import ReadBoardNetworkUseCase
from backend.domain.identifiers import EspDeviceId
from backend.presentation.api.requests.boards import BoardNetworkBody, network_command
from backend.presentation.api.responses.boards import BoardNetworkResponse, network_of
from backend.presentation.security_helpers import CurrentUserId

router = APIRouter(route_class=DishkaRoute, prefix="/esp-devices", tags=["esp-devices"])


@router.get("/{board_id}/network", response_model=BoardNetworkResponse)
async def read_board_network(
    board_id: str,
    user_id: CurrentUserId,
    use_case: FromDishka[ReadBoardNetworkUseCase],
) -> BoardNetworkResponse:
    """Возвращает сеть, которую предписано использовать плате.

    Args:
        board_id: Идентификатор платы.
        user_id: Владелец, разрешённый из bearer-токена.
        use_case: Чтение сети платы.

    Returns:
        BoardNetworkResponse: Сеть платы.

    Raises:
        BoardNotFoundError: Когда платы нет или она принадлежит другому аккаунту.
    """
    network = await use_case.execute(user_id, EspDeviceId.parse(board_id))
    if network is None:
        raise BoardNotFoundError(EspDeviceId.parse(board_id))
    return network_of(network)


@router.put("/{board_id}/network", response_model=BoardNetworkResponse)
async def write_board_network(
    board_id: str,
    body: BoardNetworkBody,
    user_id: CurrentUserId,
    use_case: FromDishka[ConfigureBoardNetworkUseCase],
) -> BoardNetworkResponse:
    """Сообщает плате сеть, которую та должна использовать.

    Настройки сохраняются, даже когда плата недоступна: плата, настроенная
    самостоятельно, ещё не знает сети сервера, и владелец вправе записать
    настройки до того, как плата появится.

    Args:
        board_id: Идентификатор платы.
        body: Сеть, которую должна использовать плата.
        user_id: Владелец, разрешённый из bearer-токена.
        use_case: Смена сети платы.

    Returns:
        BoardNetworkResponse: Сеть такой, какой она сохранена.
    """
    network = await use_case.execute(
        user_id, EspDeviceId.parse(board_id), network_command(body)
    )
    return network_of(network)
