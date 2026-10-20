"""Routes of the network of a board.

The owner of a board changes its network in the interface, and the values travel
to the board over the socket it already keeps open. The board writes them into
its own flash and reconnects, which is why nothing has to be typed into the
board a second time.

The password of the network is a secret: it travels in the request, reaches the
board and stops there. It is never part of an answer, so the interface cannot
show it even by accident.
"""

from __future__ import annotations

from dishka import FromDishka
from dishka.integrations.fastapi import DishkaRoute
from fastapi import APIRouter

from smart_home.application.dto.esp import SetNetworkCommand
from smart_home.application.errors import BoardNotFoundError
from smart_home.application.use_cases.boards.configure_board_network import (
    ConfigureBoardNetworkUseCase,
)
from smart_home.domain.identifiers import EspDeviceId
from smart_home.presentation.api.schemas import (
    BoardNetworkBody,
    BoardNetworkResponse,
    network_of,
)
from smart_home.presentation.api.security import CurrentUserId

router = APIRouter(route_class=DishkaRoute, prefix="/esp-devices", tags=["esp-devices"])


@router.get("/{board_id}/network", response_model=BoardNetworkResponse)
async def read_board_network(
    board_id: str,
    user_id: CurrentUserId,
    use_case: FromDishka[ConfigureBoardNetworkUseCase],
) -> BoardNetworkResponse:
    """Return the network a board is told to use.

    Args:
        board_id: Identifier of the board.
        user_id: Owner resolved from the bearer token.
        use_case: Change of the network of a board.

    Returns:
        BoardNetworkResponse: The network of the board.

    Raises:
        BoardNotFoundError: When the board does not exist or belongs to somebody
            else, which the error handler turns into 404.
    """
    network = await use_case.current(user_id, EspDeviceId.parse(board_id))
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
    """Tell a board which network it is to use.

    The settings are stored even when the board cannot be reached: a board that
    was set up on its own has no network the server knows of yet, and the owner
    is allowed to write the settings down before the board is there to receive
    them.

    Args:
        board_id: Identifier of the board.
        body: The network the board is to use.
        user_id: Owner resolved from the bearer token.
        use_case: Change of the network of a board.

    Returns:
        BoardNetworkResponse: The network as it was stored.
    """
    network = await use_case.execute(
        user_id,
        EspDeviceId.parse(board_id),
        SetNetworkCommand(
            ssid=body.ssid,
            password=body.password,
            host=body.host,
            server_port=body.server_port,
            socket_port=body.socket_port,
            socket_path=body.socket_path,
        ),
    )
    return network_of(network)
