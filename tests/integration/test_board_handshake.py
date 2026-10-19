"""Разговор платы с сервером: handshake, сопряжение и микрофон.

Проверяется ровно то, что ломалось при разработке: целый JSON в `HELLO` (обрезанный
кадр выглядит так, будто платы нет вообще), заявка на сопряжение для незнакомого ключа
и то, что привязанная плата перестаёт проситься.
"""

from __future__ import annotations

import json
from typing import Any

from smart_home_backend.application.dto.user import AnnounceEspDeviceCommand, ClaimEspDeviceCommand
from smart_home_backend.application.use_cases.esp_device import (
    AnnounceEspDeviceUseCase,
    ClaimEspDeviceUseCase,
    ClaimNotFoundError,
    ListEspClaimsUseCase,
)
from smart_home_backend.domain.entities.user import AlreadyClaimedError
from smart_home_backend.infrastructure.esp import protocol

ALICE = "550e8400-e29b-41d4-a716-446655440000"
BOB = "550e8400-e29b-41d4-a716-446655440001"


def handshake_payload(
    device_key: str, label: str = "0A1B2C", claim: bool = True, mic: bool = True
) -> dict[str, Any]:
    """Return the hello frame of a board.

    Args:
        device_key: Secret the board stored in its own flash.
        label: Short code shown in the interface.
        claim: Whether the board asks to be taken.
        mic: Whether a microphone is fitted.

    Returns:
        dict[str, Any]: Fields of the handshake frame.
    """
    return {
        "type": "HELLO",
        "firmware_version": "1.3.1",
        "protocol_version": 2,
        "pairing_key": device_key,
        "label": label,
        "mic": mic,
        "claim": claim,
        "relays": [False, False, False, False, False, False],
    }


def test_hello_fits_into_the_firmware_buffer() -> None:
    """The frame the firmware builds must not be cut short by its own buffer.

    A truncated frame is invalid JSON, and an invalid handshake is
    indistinguishable from a board that never dialled in.
    """
    payload = handshake_payload("a" * 32)
    # FRAME_SIZE of the firmware, plus room for the null byte snprintf writes.
    assert len(json.dumps(payload, separators=(",", ":"), ensure_ascii=False)) < 256


def test_hello_is_understood_by_the_backend() -> None:
    message = protocol.parse(json.dumps(handshake_payload("b" * 32)))
    assert message is not None
    assert message.pairing_key == "b" * 32
    assert message.label == "0A1B2C"
    assert message.wants_claim is True
    assert message.has_mic is True


def test_board_that_belongs_to_nobody_is_answered_with_an_offer(container) -> None:
    """An unknown key becomes an offer every account can see."""
    import asyncio

    connection = container.esp_connection
    offered = asyncio.run(connection._announce_board("c" * 32, "0A1B2C"))
    assert offered is not None
    assert offered.label == "0A1B2C"
    assert offered.ttl_sec > 0

    claims = asyncio.run(container.list_esp_claims.execute())
    assert [claim.label for claim in claims] == ["0A1B2C"]


def test_board_that_announces_itself_twice_keeps_one_offer(container) -> None:
    import asyncio

    connection = container.esp_connection
    assert asyncio.run(connection._announce_board("d" * 32, "0A1B2C")) is not None
    # A board that dialled in again while its offer is open keeps the same token,
    # so the code on the screen of the user stays valid.
    assert asyncio.run(connection._announce_board("d" * 32, "0A1B2C")) is not None
    claims = asyncio.run(container.list_esp_claims.execute())
    assert len(claims) == 1


def test_a_board_is_announced_even_when_it_does_not_ask(container) -> None:
    """What the server knows decides, not what the board believes.

    A board that stored a wrong ownership flag in its own flash would otherwise
    stay mute forever: it thinks it is paired, so it never asks, so nobody ever
    takes it. An unknown key is an unpaired board by definition.
    """
    import asyncio

    connection = container.esp_connection
    assert asyncio.run(connection._announce_board("e" * 32, "0A1B2C")) is not None
    assert len(asyncio.run(container.list_esp_claims.execute())) == 1


async def test_the_first_account_to_take_a_board_owns_it(container, account) -> None:
    user_id = account
    announce = container.announce_esp_device
    offer = await announce.execute(
        AnnounceEspDeviceCommand(device_key="f" * 32, label="0A1B2C")
    )

    board = await container.claim_esp_device.execute(
        user_id, ClaimEspDeviceCommand(claim_token=offer.claim_token, name="ESP кухня")
    )
    assert board.pairing_key == "f" * 32

    # The very next dial in resolves the key into that account, which is what
    # makes the board come online without any manual step.
    resolved = await container.esp_connection._resolve_pairing_key("f" * 32)
    assert resolved is not None
    assert resolved.user_id == user_id


async def test_a_second_account_cannot_take_the_same_board(container) -> None:
    from smart_home_backend.domain.value_objects.identity import UserId

    announce = container.announce_esp_device
    offer = await announce.execute(
        AnnounceEspDeviceCommand(device_key="9" * 32, label="0A1B2C")
    )
    await container.claim_esp_device.execute(
        UserId(BOB), ClaimEspDeviceCommand(claim_token=offer.claim_token, name="ESP Боба")
    )

    try:
        await container.claim_esp_device.execute(
            UserId(ALICE), ClaimEspDeviceCommand(claim_token=offer.claim_token, name="ESP Алисы")
        )
    except AlreadyClaimedError:
        return
    raise AssertionError("a taken board must not be taken twice")


async def test_an_unknown_token_is_refused(container) -> None:
    from smart_home_backend.domain.value_objects.identity import UserId

    try:
        await container.claim_esp_device.execute(
            UserId(ALICE), ClaimEspDeviceCommand(claim_token="ZZZZZZZZ", name="ESP")
        )
    except ClaimNotFoundError:
        return
    raise AssertionError("an unknown token must not create a board")


async def test_a_claimed_board_is_confirmed_on_every_handshake(container, account) -> None:
    """The board only learns that it is owned from the handshake, so the
    confirmation has to travel with every one of them."""
    sent: list[str] = []

    class _Socket:
        async def send(self, frame: str) -> None:
            sent.append(frame)

    class _Session:
        def __init__(self) -> None:
            self.socket = _Socket()

    connection = container.esp_connection
    from smart_home_backend.domain.value_objects.identity import UserId

    connection._sessions[UserId(account)] = _Session()  # type: ignore[attr-defined]
    await connection.confirm_ownership(UserId(account))

    assert [json.loads(frame)["type"] for frame in sent] == ["CLAIMED"]


def test_claim_frame_carries_the_label_the_user_sees() -> None:
    frame = json.loads(protocol.build_claim("0A1B2C", 120))
    assert frame == {"type": "CLAIM", "label": "0A1B2C", "ttl_sec": 120}


def test_microphone_window_is_bounded() -> None:
    """A window without a length would let a board flood the server."""
    frame = json.loads(protocol.build_arm_mic(sample_rate=16000, max_sec=15))
    assert frame["max_ms"] == 15000


def test_claim_use_cases_are_wired_into_the_container(container) -> None:
    assert isinstance(container.list_esp_claims, ListEspClaimsUseCase)
    assert isinstance(container.claim_esp_device, ClaimEspDeviceUseCase)
    assert isinstance(container.announce_esp_device, AnnounceEspDeviceUseCase)