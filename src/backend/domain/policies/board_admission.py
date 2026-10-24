"""Правила допуска платы, которая только что дозвонилась."""

from __future__ import annotations

from datetime import datetime
from enum import StrEnum


class AdmissionKind(StrEnum):
    """Вид ответа плате на её handshake."""

    GRANTED = "GRANTED"
    AWAITING_OWNER = "AWAITING_OWNER"
    REFUSED = "REFUSED"


class BoardAdmissionPolicy:
    """Решает, пускать ли плату и что сказать ей в ответ."""

    MINIMAL_OFFER_SEC = 1
    """Нижняя граница предложения: ноль означал бы уже просроченное сообщение."""

    @staticmethod
    def decide(key_presented: bool, known_board: bool, board_claims_owned: bool) -> AdmissionKind:
        """Возвращает вид ответа на предъявленный платой ключ.

        Решение принимает сервер: флаг в памяти платы — только кеш её последнего
        ответа сервера, и залипший флаг не имеет права заглушить плату навсегда.
        Поэтому неизвестный ключ означает плату без хозяина независимо от того, что
        о себе она думает.

        Args:
            key_presented: Назвала ли плата секрет вовсе.
            known_board: Нашёл ли сервер плату по этому секрету.
            board_claims_owned: Считает ли сама плата, что хозяин у неё есть.

        Returns:
            AdmissionKind: Пустить, объявить хозяину или отказать.
        """
        del board_claims_owned
        if not key_presented:
            return AdmissionKind.REFUSED
        return AdmissionKind.GRANTED if known_board else AdmissionKind.AWAITING_OWNER

    @staticmethod
    def offer_ttl(expires_at: datetime, now: datetime) -> int:
        """Сколько секунд предложение ещё действительно.

        Args:
            expires_at: Момент, после которого предложение недействительно.
            now: Текущий момент.

        Returns:
            int: Секунды не меньше нижней границы.
        """
        remaining = int((expires_at - now).total_seconds())
        return max(remaining, BoardAdmissionPolicy.MINIMAL_OFFER_SEC)
