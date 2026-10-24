"""Ответы про платы: сопряжение, предложения и сеть."""

from __future__ import annotations

from datetime import datetime

from backend.application.dto.views.board_claim_view import BoardClaimView
from backend.application.dto.views.board_network_view import BoardNetworkView
from backend.application.dto.views.board_view import BoardView
from backend.application.dto.views.paired_board_view import PairedBoardView
from backend.presentation.api.responses.common import StrictModel


class BoardResponse(StrictModel):
    """Одна плата такой, какой её видит интерфейс.

    Attributes:
        id: Идентификатор платы.
        name: Имя, показанное человеку.
        online: Подключена ли плата сейчас.
        last_seen_at: Момент последнего успешного handshake, или None.
        current_ssid: Сеть, о которой плата сообщила сама, или None.
    """

    id: str
    name: str
    online: bool
    last_seen_at: datetime | None
    current_ssid: str | None


class BoardClaimResponse(StrictModel):
    """Предложение платы, которая ждёт хозяина.

    Attributes:
        id: Идентификатор предложения.
        label: Короткий код, показанный рядом с платой.
        claim_token: Токен, которым плату забирают.
        announced_at: Момент, когда плата объявила о себе.
        expires_at: Момент, после которого предложение недействительно.
    """

    id: str
    label: str
    claim_token: str
    announced_at: datetime
    expires_at: datetime


class BoardPairedResponse(StrictModel):
    """Только что сопряжённая плата, у которой ключ открыт ровно один раз.

    Attributes:
        id: Идентификатор платы.
        name: Имя, показанное человеку.
        pairing_key: Секрет, который плата обязана предъявлять при звонке.
    """

    id: str
    name: str
    pairing_key: str


class BoardNetworkResponse(StrictModel):
    """Сеть платы такой, какой её видит интерфейс.

    Attributes:
        board_id: Идентификатор платы.
        ssid: Имя беспроводной сети, предписанное плате.
        host: Адрес сервера, которому плата докладывается.
        server_port: Порт обычного интерфейса этого сервера.
        socket_port: Порт доски на сервере.
        socket_path: Путь доски на сервере.
        configured: Есть ли у платы собственная сеть.
        updated_at: Момент записи настроек, или None.
    """

    board_id: str
    ssid: str
    host: str
    server_port: int
    socket_port: int
    socket_path: str
    configured: bool
    updated_at: datetime | None


def board_of(board: BoardView) -> BoardResponse:
    """Возвращает тело платы.

    Args:
        board: Плата такой, какой её видит прикладной слой.

    Returns:
        BoardResponse: Тело платы.
    """
    return BoardResponse(
        id=str(board.id),
        name=board.name,
        online=board.online,
        last_seen_at=board.last_seen_at,
        current_ssid=board.current_ssid,
    )


def claim_of(claim: BoardClaimView) -> BoardClaimResponse:
    """Возвращает тело предложения платы.

    Args:
        claim: Предложение такое, каким его видит прикладной слой.

    Returns:
        BoardClaimResponse: Тело предложения.
    """
    return BoardClaimResponse(
        id=str(claim.id),
        label=claim.label,
        claim_token=claim.claim_token,
        announced_at=claim.announced_at,
        expires_at=claim.expires_at,
    )


def paired_of(paired: PairedBoardView) -> BoardPairedResponse:
    """Возвращает тело сопряжённой платы вместе с её ключом.

    Args:
        paired: Результат сопряжения прикладного слоя.

    Returns:
        BoardPairedResponse: Тело сопряжённой платы.
    """
    return BoardPairedResponse(
        id=str(paired.board.id),
        name=paired.board.name,
        pairing_key=paired.pairing_key,
    )


def network_of(network: BoardNetworkView) -> BoardNetworkResponse:
    """Возвращает тело сети платы.

    Args:
        network: Сеть такая, какой её видит прикладной слой.

    Returns:
        BoardNetworkResponse: Тело сети.
    """
    return BoardNetworkResponse(
        board_id=str(network.board_id),
        ssid=network.ssid,
        host=network.host,
        server_port=network.server_port,
        socket_port=network.socket_port,
        socket_path=network.socket_path,
        configured=network.configured,
        updated_at=network.updated_at,
    )
