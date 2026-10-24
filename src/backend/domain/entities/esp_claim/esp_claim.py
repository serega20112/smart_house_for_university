"""
Предложение забрать плату, у которой ещё нет хозяина.

Открытое предложение — часть жизненного цикла платы, а не отдельный корень:
внутри него нет сущностей, а гонку «кто забрал первым» решает хранилище.
"""

from __future__ import annotations

import secrets
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Self

from backend.domain.exceptions import ClaimAlreadyTakenError, ClaimExpiredError
from backend.domain.identifiers import EspClaimId, UserId
from backend.domain.value_objects.boards.pairing_key import PairingKey

TOKEN_ALPHABET = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"
TOKEN_LENGTH = 8
LABEL_LENGTH = 6


@dataclass(frozen=True, slots=True)
class EspClaim:
    """Одна объявленная плата, которая ждёт себе хозяина.

    Attributes:
        id: Идентификатор, выданный при создании.
        device_key: Секрет, который плата предъявляет при соединении.
        label: Короткий код, показанный в интерфейсе.
        claim_token: Токен именно этого объявления.
        announced_at: Момент, когда плата объявила о себе.
        expires_at: Момент, после которого предложение недействительно.
        claimed_by: Аккаунт, который её забрал, или None пока открыто.
    """

    id: EspClaimId
    device_key: PairingKey
    label: str
    claim_token: str
    announced_at: datetime
    expires_at: datetime
    claimed_by: UserId | None = None

    @property
    def is_open(self) -> bool:
        """Сообщает, не забрал ли предложение ещё никто."""
        return self.claimed_by is None

    def is_valid_at(self, moment: datetime) -> bool:
        """Сообщает, можно ли забрать предложение в указанный момент.

        Args:
            moment: Момент, относительно которого решают.

        Returns:
            bool: True, пока предложение открыто и не просрочено.
        """
        return self.is_open and moment < self.expires_at

    def taken_by(self, user_id: UserId) -> EspClaim:
        """Возвращает то же предложение, ставя его владельцем аккаунт.

        Args:
            user_id: Аккаунт, который забирает плату.

        Returns:
            EspClaim: Забранное предложение.

        Raises:
            ClaimAlreadyTakenError: Когда до этого её забрал кто-то другой.
            ClaimExpiredError: Когда срок предложения вышел.
        """
        if not self.is_open:
            raise ClaimAlreadyTakenError()
        return EspClaim(
            id=self.id,
            device_key=self.device_key,
            label=self.label,
            claim_token=self.claim_token,
            announced_at=self.announced_at,
            expires_at=self.expires_at,
            claimed_by=user_id,
        )

    def refuse_if_not_usable(self, now: datetime) -> None:
        """Отказывает предложению, которое больше нельзя забрать.

        Args:
            now: Момент, когда попытку забрать сделали.

        Raises:
            ClaimAlreadyTakenError: Когда до этого её забрал кто-то другой.
            ClaimExpiredError: Когда срок предложения вышел.
        """
        if not self.is_open:
            raise ClaimAlreadyTakenError()
        if now >= self.expires_at:
            raise ClaimExpiredError()

    @classmethod
    def announce(
        cls,
        device_key: PairingKey,
        label: str,
        announced_at: datetime,
        ttl_sec: int,
    ) -> Self:
        """Строит предложение для платы, которая только что объявилась.

        Args:
            device_key: Секрет, который плата предъявит при соединении.
            label: Короткий код для интерфейса.
            announced_at: Момент объявления платы.
            ttl_sec: Сколько времени предложение остаётся действительным.

        Returns:
            Self: Открытое предложение.
        """
        return cls(
            id=EspClaimId.generate(),
            device_key=device_key,
            label=label[:LABEL_LENGTH].upper(),
            claim_token=new_claim_token(),
            announced_at=announced_at,
            expires_at=announced_at + timedelta(seconds=ttl_sec),
        )

    @classmethod
    def label_from_key(cls, device_key: PairingKey) -> str:
        """Возвращает код для платы, которая сама его не назвала.

        Args:
            device_key: Секрет, который плата предъявила при соединении.

        Returns:
            str: Короткий код, составленный из ключа.
        """
        return device_key.value[:LABEL_LENGTH].upper()


def new_claim_token() -> str:
    """Вырабатывает токен одного объявления.

    Из алфавита убраны буквы и цифры, которые человек путает, списывая код с одного
    экрана и набирая на другом, -- а предложение смотрят именно так: с телефона
    рядом с платой.

    Returns:
        str: Токен объявления.
    """
    return "".join(secrets.choice(TOKEN_ALPHABET) for _ in range(TOKEN_LENGTH))
