"""Routes of the network of a board.

The owner of a board changes its network in the interface, and the values travel
to the board over the socket it already keeps open. The board writes them into
its own flash and reconnects, which is why nothing has to be typed into the
board a second time.

The password of the network is a secret: it travels in the request, reaches the
board and stops there. It is never part of an answer, so the interface cannot
show it even by accident.

The annotations of this module are written out rather than postponed: the
injection of the container replaces the globals of the handler, and a postponed
annotation would be a string nobody can resolve afterwards.
"""

from typing import Annotated

from dishka.integrations.fastapi import FromDishka, inject
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel, Field

from backend.application.dto.esp import BoardNetworkView, SetNetworkCommand
from backend.application.errors import BoardNotFoundError
from backend.application.ports.services import SessionTokenIssuer
from backend.application.use_cases.boards.configure_board_network import (
    ConfigureBoardNetworkUseCase,
)
from backend.domain.exceptions import InvalidNetworkProfileError
from backend.domain.identifiers import EspDeviceId, MalformedIdentifierError, UserId

router = APIRouter(prefix="/esp-devices", tags=["esp-devices"])

bearer_scheme = HTTPBearer(auto_error=False)

UNAUTHORIZED = "Требуется авторизация"
BOARD_NOT_FOUND = "Плата не найдена"
NETWORK_NOT_CONFIGURED = "Сеть платы не настроена"
MALFORMED_IDENTIFIER = "Некорректный идентификатор платы"


class BoardNetworkBody(BaseModel):
    """The network a board is to use.

    Args:
        ssid: Name of the wireless network.
        password: Password of that network, empty when the network is open.
        host: Address of the server the board reports to.
        server_port: Port of the ordinary interface of that server.
        socket_port: Port of the board socket of that server.
        socket_path: Path of the board socket of that server.

    Returns:
        None.
    """

    ssid: str = Field(min_length=1, max_length=32)
    password: str = Field(default="", max_length=64)
    host: str = Field(min_length=1, max_length=64)
    server_port: int = Field(default=8000, ge=1, le=65535)
    socket_port: int = Field(default=8001, ge=1, le=65535)
    socket_path: str = Field(default="/ws/board", min_length=1, max_length=64)


class BoardNetworkResponse(BaseModel):
    """The network of a board as the interface needs it.

    Args:
        board_id: Identifier of the board.
        ssid: Name of the wireless network the board is to use.
        host: Address of the server the board reports to.
        server_port: Port of the ordinary interface of that server.
        socket_port: Port of the board socket of that server.
        socket_path: Path of the board socket of that server.
        updated_at: Moment the settings were written, or None.

    Returns:
        None.
    """

    board_id: str
    ssid: str
    host: str
    server_port: int
    socket_port: int
    socket_path: str
    updated_at: str | None = None


def _owner_of(
    tokens: SessionTokenIssuer,
    credentials: HTTPAuthorizationCredentials | None,
) -> UserId:
    """Return the account the request was authorized as.

    Args:
        tokens: Issuer of the session tokens.
        credentials: Bearer token presented by the client.

    Returns:
        UserId: Owner the token was issued for.

    Raises:
        HTTPException: When the token is missing or not valid.
    """
    if credentials is None or not credentials.credentials:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, UNAUTHORIZED)
    owner = tokens.resolve(credentials.credentials)
    if owner is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, UNAUTHORIZED)
    return owner


@router.get("/{board_id}/network")
@inject
async def read_board_network(
    board_id: str,
    tokens: Annotated[SessionTokenIssuer, FromDishka()],
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer_scheme)],
    use_case: Annotated[ConfigureBoardNetworkUseCase, FromDishka()],
) -> BoardNetworkResponse:
    """Return the network a board is told to use.

    Args:
        board_id: Identifier of the board.
        tokens: Issuer of the session tokens.
        credentials: Bearer token presented by the client.
        use_case: Change of the network of a board.

    Returns:
        BoardNetworkResponse: The network of the board.

    Raises:
        HTTPException: When the board does not exist, was never configured or
            the identifier is malformed.
    """
    owner = _owner_of(tokens, credentials)
    identifier = _parse_board_id(board_id)
    try:
        network = await use_case.current(owner, identifier)
    except BoardNotFoundError as exc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, BOARD_NOT_FOUND) from exc
    if network is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, NETWORK_NOT_CONFIGURED)
    return _response_of(network)


@router.put("/{board_id}/network")
@inject
async def write_board_network(
    board_id: str,
    body: BoardNetworkBody,
    tokens: Annotated[SessionTokenIssuer, FromDishka()],
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer_scheme)],
    use_case: Annotated[ConfigureBoardNetworkUseCase, FromDishka()],
) -> BoardNetworkResponse:
    """Tell a board which network it is to use.

    The settings are stored even when the board cannot be reached: a board that
    was set up on its own has no network the server knows of yet, and the owner
    is allowed to write the settings down before the board is there to receive
    them.

    Args:
        board_id: Identifier of the board.
        body: The network the board is to use.
        tokens: Issuer of the session tokens.
        credentials: Bearer token presented by the client.
        use_case: Change of the network of a board.

    Returns:
        BoardNetworkResponse: The network as it was stored.

    Raises:
        HTTPException: When the board does not exist, the identifier is
            malformed or the values cannot be used.
    """
    owner = _owner_of(tokens, credentials)
    identifier = _parse_board_id(board_id)
    try:
        network = await use_case.execute(
            owner,
            identifier,
            SetNetworkCommand(
                ssid=body.ssid,
                password=body.password,
                host=body.host,
                server_port=body.server_port,
                socket_port=body.socket_port,
                socket_path=body.socket_path,
            ),
        )
    except BoardNotFoundError as exc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, BOARD_NOT_FOUND) from exc
    except InvalidNetworkProfileError as exc:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, str(exc)) from exc
    return _response_of(network)


def _parse_board_id(raw: str) -> EspDeviceId:
    """Read the identifier of a board.

    Args:
        raw: Identifier as it arrived.

    Returns:
        EspDeviceId: Identifier of the board.

    Raises:
        HTTPException: When the identifier is not a UUID.
    """
    try:
        return EspDeviceId.parse(raw)
    except MalformedIdentifierError as exc:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, MALFORMED_IDENTIFIER) from exc


def _response_of(network: BoardNetworkView) -> BoardNetworkResponse:
    """Build the answer of the network of a board.

    Args:
        network: The network as the application layer described it.

    Returns:
        BoardNetworkResponse: The network as the interface needs it.
    """
    return BoardNetworkResponse(
        board_id=str(network.board_id),
        ssid=network.ssid,
        host=network.host,
        server_port=network.server_port,
        socket_port=network.socket_port,
        socket_path=network.socket_path,
        updated_at=None if network.updated_at is None else network.updated_at.isoformat(),
    )
