"""Предложение от неподключённой платы в том виде, в каком его показывают."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from backend.domain.identifiers import EspClaimId


@dataclass(frozen=True, slots=True)
class BoardClaimView:
    """Открытое предложение платы, которую ещё не привязали.

    Ключ устройства здесь никогда не передаётся: это credential платы, а человеку
    нужны только код и токен предложения.

    Attributes:
        id: Идентификатор предложения.
        label: Короткий код рядом с платой.
        claim_token: Токен, по которому плату забирают.
        announced_at: Момент, когда плата заявила о себе.
        expires_at: Момент, после которого предложение не действительно.
    """

    id: EspClaimId
    label: str
    claim_token: str
    announced_at: datetime
    expires_at: datetime
