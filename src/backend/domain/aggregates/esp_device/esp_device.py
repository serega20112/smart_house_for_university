"""Плата, сопряжённая с аккаунтом.

Плата дозванивается сама, поэтому единственное, что привязывает её к человеку, — ключ,
который она предъявляет при handshake. Ключ и есть учётные данные, а аккаунт — владелец
всего, что плата сообщает.

Плата ещё говорит, в какой сети она находится, и этот ответ хранится рядом с моментом
последнего handshake: оба значения — то о себе, что плата рассказала в последний раз,
когда её было видно.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Self

from backend.domain.identifiers import EspDeviceId, UserId
from backend.domain.value_objects.boards.board_name import BoardName
from backend.domain.value_objects.boards.pairing_key import PairingKey


@dataclass(frozen=True, slots=True)
class EspDevice:
    """Плата, сопряжённая с одним аккаунтом.

    Attributes:
        id: Идентификатор, выданный при создании.
        user_id: Владелец платы и всего, что она питает.
        name: Имя, показанное человеку.
        pairing_key: Секрет, который плата предъявляет при соединении.
        created_at: Момент сопряжения платы.
        last_seen_at: Момент последнего успешного handshake, или None.
        current_ssid: Сеть, о которой сообщила плата, или None, пока не сообщала.

    Raises:
        InvalidBoardNameError: Когда имя пустое или слишком длинное.
    """

    id: EspDeviceId
    user_id: UserId
    name: str
    pairing_key: PairingKey
    created_at: datetime
    last_seen_at: datetime | None = None
    current_ssid: str | None = None

    def __post_init__(self) -> None:
        """Проверяет имя платы.

        Raises:
            InvalidBoardNameError: Когда имя пустое или слишком длинное.
        """
        trimmed = BoardName.parse(self.name).value
        object.__setattr__(self, "name", trimmed)

    @classmethod
    def pair(
        cls,
        user_id: UserId,
        name: str,
        pairing_key: PairingKey,
        paired_at: datetime,
    ) -> Self:
        """Строит только что сопряжённую плату.

        Args:
            user_id: Владелец платы.
            name: Имя, показанное человеку.
            pairing_key: Секрет, который плата будет предъявлять при соединении.
            paired_at: Момент сопряжения.

        Returns:
            Self: Созданная плата.
        """
        return cls(
            id=EspDeviceId.generate(),
            user_id=user_id,
            name=name,
            pairing_key=pairing_key,
            created_at=paired_at,
        )

    def seen(self, at: datetime, ssid: str | None) -> EspDevice:
        """Возвращает плату такой, какой её видели в последний раз.

        Args:
            at: Момент handshake.
            ssid: Сеть, о которой сообщила плата, или None.

        Returns:
            EspDevice: Плата с тем, что она сообщила.
        """
        return EspDevice(
            id=self.id,
            user_id=self.user_id,
            name=self.name,
            pairing_key=self.pairing_key,
            created_at=self.created_at,
            last_seen_at=at,
            current_ssid=ssid,
        )
