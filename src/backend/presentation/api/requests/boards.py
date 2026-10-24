"""Тела запросов платы и перевод их в команды приложения."""

from __future__ import annotations

from pydantic import Field

from backend.application.dto.boards.claim_board_command import ClaimBoardCommand
from backend.application.dto.boards.pair_board_command import PairBoardCommand
from backend.application.dto.boards.set_network_command import SetNetworkCommand
from backend.domain.value_objects.boards.board_name import BoardName
from backend.presentation.api.base import StrictModel

NAME_MAX_LENGTH = BoardName.MAX_LENGTH
SSID_MAX_LENGTH = 64
PASSWORD_MAX_LENGTH = 128
ADDRESS_MAX_LENGTH = 255
PORT_MIN = 1
PORT_MAX = 65535


class ClaimBoardBody(StrictModel):
    """Запрос на взятие объявленной платы.

    Attributes:
        claim_token: Токен предложения.
        name: Имя, которое человек даёт плате.
    """

    claim_token: str
    name: str = Field(min_length=1, max_length=NAME_MAX_LENGTH)


class PairBoardBody(StrictModel):
    """Запрос на ручное сопряжение платы.

    Attributes:
        name: Имя, показанное человеку.
        pairing_key: Выбранный человеком ключ или None, чтобы его выработала система.
    """

    name: str = Field(min_length=1, max_length=NAME_MAX_LENGTH)
    pairing_key: str | None = None


class BoardNetworkBody(StrictModel):
    """Сеть, которую плате предписано использовать.

    Attributes:
        ssid: Имя беспроводной сети.
        password: Пароль сети, пустой, когда сеть открыта.
        host: Адрес сервера, которому плата докладывается.
        server_port: Порт обычного интерфейса этого сервера.
        socket_port: Порт доски на сервере.
        socket_path: Путь доски на сервере.
    """

    ssid: str = Field(min_length=1, max_length=SSID_MAX_LENGTH)
    password: str = Field(max_length=PASSWORD_MAX_LENGTH)
    host: str = Field(min_length=1, max_length=ADDRESS_MAX_LENGTH)
    server_port: int = Field(ge=PORT_MIN, le=PORT_MAX)
    socket_port: int = Field(ge=PORT_MIN, le=PORT_MAX)
    socket_path: str = Field(min_length=1, max_length=ADDRESS_MAX_LENGTH)


def claim_command(body: ClaimBoardBody) -> ClaimBoardCommand:
    """Возвращает команду взятия платы.

    Args:
        body: Токен предложения и выбранное имя.

    Returns:
        ClaimBoardCommand: Команда, понятная сценарию приложения.
    """
    return ClaimBoardCommand(claim_token=body.claim_token, name=body.name)


def pair_command(body: PairBoardBody) -> PairBoardCommand:
    """Возвращает команду сопряжения платы.

    Args:
        body: Имя платы и, возможно, выбранный ключ.

    Returns:
        PairBoardCommand: Команда, понятная сценарию приложения.
    """
    return PairBoardCommand(name=body.name, pairing_key=body.pairing_key)


def network_command(body: BoardNetworkBody) -> SetNetworkCommand:
    """Возвращает команду смены сети платы.

    Args:
        body: Сеть, которую должна использовать плата.

    Returns:
        SetNetworkCommand: Команда, понятная сценарию приложения.
    """
    return SetNetworkCommand(
        ssid=body.ssid,
        password=body.password,
        host=body.host,
        server_port=body.server_port,
        socket_port=body.socket_port,
        socket_path=body.socket_path,
    )
