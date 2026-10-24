"""Мапперы плат, их предложений и сети."""

from __future__ import annotations

from backend.domain.aggregates.esp_device.esp_device import EspDevice
from backend.domain.entities.boards.board_network import BoardNetwork
from backend.domain.entities.esp_claim.esp_claim import EspClaim
from backend.domain.identifiers import EspClaimId, EspDeviceId, UserId
from backend.domain.value_objects.boards.network_profile import NetworkProfile
from backend.domain.value_objects.boards.pairing_key import PairingKey
from backend.infrastructure.database.mappers.base import as_utc
from backend.infrastructure.database.models import (
    BoardNetworkModel,
    EspClaimModel,
    EspDeviceModel,
)


def board_to_row(board: EspDevice) -> EspDeviceModel:
    """Строит строку, описывающую сопряжённую плату.

    Args:
        board: Плата для сериализации.

    Returns:
        EspDeviceModel: Новая строка, описывающая плату.
    """
    return EspDeviceModel(
        id=board.id.value,
        user_id=board.user_id.value,
        name=board.name,
        pairing_key=board.pairing_key.value,
        created_at=board.created_at,
        last_seen_at=board.last_seen_at,
        current_ssid=board.current_ssid,
    )


def board_from_row(row: EspDeviceModel) -> EspDevice:
    """Строит плату, описанную строкой.

    Args:
        row: Строка для десериализации.

    Returns:
        EspDevice: Восстановленная плата.
    """
    return EspDevice(
        id=EspDeviceId.parse(row.id),
        user_id=UserId.parse(row.user_id),
        name=row.name,
        pairing_key=PairingKey(row.pairing_key),
        created_at=as_utc(row.created_at),
        last_seen_at=None if row.last_seen_at is None else as_utc(row.last_seen_at),
        current_ssid=row.current_ssid,
    )


def claim_to_row(claim: EspClaim) -> EspClaimModel:
    """Строит строку, описывающую объявленную плату без хозяина.

    Args:
        claim: Предложение для сериализации.

    Returns:
        EspClaimModel: Новая строка, описывающая предложение.
    """
    return EspClaimModel(
        id=claim.id.value,
        device_key=claim.device_key.value,
        label=claim.label,
        claim_token=claim.claim_token,
        announced_at=claim.announced_at,
        expires_at=claim.expires_at,
        claimed_by=None if claim.claimed_by is None else claim.claimed_by.value,
    )


def claim_from_row(row: EspClaimModel) -> EspClaim:
    """Строит предложение, описанное строкой.

    Args:
        row: Строка для десериализации.

    Returns:
        EspClaim: Восстановленное предложение.
    """
    return EspClaim(
        id=EspClaimId.parse(row.id),
        device_key=PairingKey(row.device_key),
        label=row.label,
        claim_token=row.claim_token,
        announced_at=as_utc(row.announced_at),
        expires_at=as_utc(row.expires_at),
        claimed_by=None if row.claimed_by is None else UserId.parse(row.claimed_by),
    )


def network_to_row(network: BoardNetwork) -> BoardNetworkModel:
    """Строит строку, описывающую сеть платы.

    Args:
        network: Сеть для сериализации.

    Returns:
        BoardNetworkModel: Новая строка, описывающая сеть.
    """
    profile = network.profile
    return BoardNetworkModel(
        board_id=network.board_id.value,
        user_id=network.user_id.value,
        ssid=profile.ssid,
        password=profile.password,
        host=profile.host,
        server_port=profile.server_port,
        socket_port=profile.socket_port,
        socket_path=profile.socket_path,
        updated_at=network.updated_at,
    )


def network_from_row(row: BoardNetworkModel) -> BoardNetwork:
    """Строит сеть, описанную строкой.

    Args:
        row: Строка для десериализации.

    Returns:
        BoardNetwork: Восстановленная сеть.
    """
    return BoardNetwork(
        board_id=EspDeviceId.parse(row.board_id),
        user_id=UserId.parse(row.user_id),
        profile=NetworkProfile(
            ssid=row.ssid,
            password=row.password,
            host=row.host,
            server_port=row.server_port,
            socket_port=row.socket_port,
            socket_path=row.socket_path,
        ),
        updated_at=as_utc(row.updated_at),
    )
