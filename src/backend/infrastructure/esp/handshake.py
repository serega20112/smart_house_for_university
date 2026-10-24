"""Первый кадр платы: тот ли путь, та ли сеть и кому она принадлежит.

Плата звонит сама, поэтому handshake решает всё до того, как ей будет отправлена
хотя бы одна команда: неизвестный ключ ещё не имеет хозяина, а неверный кадр не
позволяет понять, какой это дом вовсе.
"""

from __future__ import annotations

import asyncio
from contextlib import suppress

from websockets.asyncio.server import ServerConnection

from backend.infrastructure.esp import protocol
from backend.infrastructure.esp.onboarding import (
    BoardAnnouncement,
    BoardIdentity,
    BoardOnboardingGateway,
)
from backend.infrastructure.logging import get_logger

log = get_logger("esp.handshake")

CLOSE_WRONG_PATH = 4404
CLOSE_UNKNOWN_KEY = 4401
CLOSE_AWAITING_OWNER = 4403


def matches_path(connection: ServerConnection, path: str) -> bool:
    """True, когда плата постучалась на путь, который сервер держит для плат."""
    request = getattr(connection, "request", None)
    actual = getattr(request, "path", None) or getattr(connection, "path", "")
    return actual in (path, f"{path}/")


async def greet(
    connection: ServerConnection,
    onboarding: BoardOnboardingGateway,
    handshake_timeout_sec: float,
) -> BoardIdentity | None:
    """Прочитывает handshake платы и возвращает её владельца.

    Каждый отказ уже закрыт сокетом с тем кодом, по которому плата понимает, что
    ей делать: неизвестный ключ уходит ждать хозяина, кривый кадр и таймаут не
    дают ни того, ни другого, и плата останется на переподключении.

    Args:
        connection: Соединение платы.
        onboarding: Шлюз, знающий, кому принадлежит ключ.
        handshake_timeout_sec: Сколько секунд ждём первый кадр.

    Returns:
        BoardIdentity | None: Владелец платы, либо None, когда соединения не будет.
    """
    raw = await _read_frame(connection, handshake_timeout_sec)
    if raw is None:
        return None
    try:
        frame = protocol.parse_inbound(raw)
    except protocol.MalformedFrameError as error:
        log.warning("esp.handshake_malformed", error=str(error))
        await connection.close(code=CLOSE_UNKNOWN_KEY, reason="malformed handshake")
        return None
    identity = await _authenticate(onboarding, frame)
    if isinstance(identity, BoardAnnouncement):
        await offer_claim(connection, identity)
        return None
    if identity is None:
        await connection.close(code=CLOSE_UNKNOWN_KEY, reason="unknown pairing key")
        return None
    return identity


async def offer_claim(connection: ServerConnection, offered: BoardAnnouncement) -> None:
    """Сообщает плате, что она узнала систему и ждёт хозяина.

    Соединение закрывается намеренно: плата никому не принадлежит, поэтому ни
    одной команды ей отправлять нельзя. Она позвонит сама, и к этому моменту
    забравший её аккаунт уже будет сохранён.

    Args:
        connection: Соединение не сопряжённой платы.
        offered: Открытое предложение этой платы.
    """
    frame = protocol.ClaimFrame(label=offered.label, ttl_sec=offered.ttl_sec)
    with suppress(Exception):
        await connection.send(frame.to_json())
    await connection.close(code=CLOSE_AWAITING_OWNER, reason="awaiting owner")
    log.info("esp.board_announced", label=offered.label, ttl_sec=offered.ttl_sec)


async def _read_frame(connection: ServerConnection, timeout_sec: float) -> str | None:
    """Ждёт первую текстовую рамку соединения."""
    try:
        raw = await asyncio.wait_for(connection.recv(), timeout=timeout_sec)
    except TimeoutError:
        log.warning("esp.handshake_timeout")
        await connection.close(code=CLOSE_UNKNOWN_KEY, reason="handshake timeout")
        return None
    except Exception as error:
        log.warning("esp.handshake_failed", error=str(error))
        return None
    if isinstance(raw, bytes | bytearray):
        log.warning(
            "esp.handshake_binary",
            size=len(raw),
            head=bytes(raw[:60]).decode("utf-8", "replace"),
        )
        return None
    return raw


async def _authenticate(
    onboarding: BoardOnboardingGateway, frame: protocol.InboundFrame
) -> BoardIdentity | BoardAnnouncement | None:
    """Разбирает ключ платы: владелец, предложение или незваный гость."""
    if not isinstance(frame, protocol.HelloFrame) or not frame.pairing_key:
        log.warning("esp.handshake_without_key")
        return None
    identity = await onboarding.resolve_pairing_key(frame.pairing_key)
    if identity is not None:
        await onboarding.record_last_seen(identity.board_id, frame.ssid)
        return identity
    offered = await onboarding.announce(frame.pairing_key, frame.label)
    if offered is None:
        log.warning("esp.board_not_announced", label=frame.label)
    return offered


__all__ = [
    "CLOSE_AWAITING_OWNER",
    "CLOSE_UNKNOWN_KEY",
    "CLOSE_WRONG_PATH",
    "greet",
    "matches_path",
    "offer_claim",
]
