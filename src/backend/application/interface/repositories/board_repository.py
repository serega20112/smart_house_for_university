"""Хранилища плат.

Плата, которая уже принадлежит аккаунту, и плата, которая владельца ещё не нашла,
— две разные вещи с двумя жизненными циклами, поэтому у них два репозитория вместо
одного с флагом внутри. Сеть платы — третья: она меняется по своему расписанию,
надолго пережив взятие платы, и живёт в отдельном репозитории.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import datetime

from backend.application.interface.repositories.base import (
    Creator,
    Deleter,
    ListAll,
    Reader,
)
from backend.domain.aggregates.board_network.board_network import BoardNetwork
from backend.domain.aggregates.esp_claim.esp_claim import EspClaim
from backend.domain.aggregates.esp_device.esp_device import EspDevice
from backend.domain.identifiers import EspClaimId, EspDeviceId, UserId


class BoardRepository(
    Creator[EspDevice],
    Reader[EspDevice, EspDeviceId],
    Deleter[EspDeviceId],
    ListAll[EspDevice],
):
    """Хранилище плат, сопряжённых с аккаунтами.

    Изменения платы — не правка строки, а событие соединения, поэтому вместо
    `update` здесь `mark_seen`.
    """

    @abstractmethod
    async def get_by_key(self, pairing_key: str) -> EspDevice | None:
        """Возвращает плату, предъявившую ключ сопряжения."""

    @abstractmethod
    async def mark_seen(
        self, board_id: EspDeviceId, seen_at: datetime, ssid: str | None = None
    ) -> None:
        """Записывает, что плата только что подключилась."""


class ClaimRepository(Creator[EspClaim]):
    """Хранилище объявленных плат, которые ждут владельца."""

    @abstractmethod
    async def current_for(self, device_key: str) -> EspClaim | None:
        """Возвращает текущее предложение платы по её ключу."""

    @abstractmethod
    async def open_with_token(self, claim_token: str) -> EspClaim | None:
        """Возвращает предложение по токену, который видит человек."""

    @abstractmethod
    async def all_open(self) -> list[EspClaim]:
        """Возвращает все предложения, которые ещё никто не взял."""

    @abstractmethod
    async def take(self, claim_id: EspClaimId, user_id: UserId) -> bool:
        """Условно записывает взятие предложения.

        Запись условная, поэтому два аккаунта, нажавшие кнопку одновременно,
        дадут ровно одного владельца: проигравший увидит False.
        """

    @abstractmethod
    async def delete_expired(self, before: datetime) -> int:
        """Удаляет истёкшие предложения, возвращая их число.

        Это команда, а не побочный эффект чтения: тот, кто просто смотрит список,
        базу данных не меняет.
        """


class BoardNetworkRepository(ABC):
    """Хранилище сети, которую предписано использовать плате."""

    @abstractmethod
    async def get(self, board_id: EspDeviceId) -> BoardNetwork | None:
        """Возвращает сеть платы или None, если её никогда не настраивали."""

    @abstractmethod
    async def save(self, network: BoardNetwork) -> None:
        """Сохраняет сеть платы."""

    @abstractmethod
    async def delete(self, board_id: EspDeviceId) -> bool:
        """Убирает сеть платы, возвращая True, если она была."""
