"""Плата, которую человек забирает из интерфейса."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class ClaimBoardCommand:
    """Значения запроса забрать плату.

    Attributes:
        claim_token: Токен предложения, показанного рядом с платой.
        name: Имя, которое человек хочет дать плате.
    """

    claim_token: str
    name: str
