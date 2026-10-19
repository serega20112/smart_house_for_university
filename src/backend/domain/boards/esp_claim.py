"""A board that is waiting to be taken by an account.

The board generates its own key on first boot and keeps it in its own flash, so
nothing has to be compiled into the firmware and nobody has to open the IDE. The
backend has never seen that key, so the board is announced as a claim: a short
label shown in the interface, a token that belongs to that one announcement, and a
moment after which the offer stops being valid.

Two rules keep this safe with several accounts on one server: the board has to ask
for it by being held, and the first account that takes the token owns the board.
"""

from __future__ import annotations

import secrets
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Self

from backend.domain.boards.pairing_key import PairingKey
from backend.domain.exceptions import ClaimAlreadyTakenError, ClaimExpiredError
from backend.domain.identifiers import EspClaimId, UserId

TOKEN_ALPHABET = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"
TOKEN_LENGTH = 8
LABEL_LENGTH = 6


@dataclass(frozen=True, slots=True)
class EspClaim:
    """One announced board waiting for an account to take it.

    Args:
        id: Identifier assigned at creation.
        device_key: Secret the board presents while connecting.
        label: Short code shown in the interface.
        claim_token: Token of this particular announcement.
        announced_at: Moment the board announced itself.
        expires_at: Moment the offer stops being valid.
        claimed_by: Account that took it, or None while it is open.

    Returns:
        None.
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
        """Return whether nobody took the offer yet.

        Returns:
            bool: True while the claim is unclaimed.
        """
        return self.claimed_by is None

    def is_valid_at(self, moment: datetime) -> bool:
        """Return whether the offer may still be taken at a moment.

        Args:
            moment: Moment to judge at.

        Returns:
            bool: True while the claim is open and not expired.
        """
        return self.is_open and moment < self.expires_at

    def taken_by(self, user_id: UserId) -> Self:
        """Return the same offer owned by an account.

        Args:
            user_id: Account taking the board.

        Returns:
            Self: Claimed offer.

        Raises:
            ClaimAlreadyTakenError: When somebody else already took it.
            ClaimExpiredError: When the offer window has closed.
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
        """Refuse the offer when it can no longer be taken.

        Args:
            now: Moment the takeover was attempted at.

        Returns:
            None.

        Raises:
            ClaimAlreadyTakenError: When somebody else already took it.
            ClaimExpiredError: When the offer window has closed.
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
        """Build an offer for a board that just announced itself.

        Args:
            device_key: Secret the board presents while connecting.
            label: Short code shown in the interface.
            announced_at: Moment the board announced itself.
            ttl_sec: How long the offer stays valid.

        Returns:
            Self: Open claim.
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
        """Return the code to show for a board that reported none.

        Args:
            device_key: Secret the board presented while connecting.

        Returns:
            str: Short code derived from the key.
        """
        return device_key.value[:LABEL_LENGTH].upper()


def new_claim_token() -> str:
    """Produce a token for one announcement.

    The alphabet leaves out characters a person could mix up when reading a code
    off another screen, which is not far fetched when the offer is shown on a
    phone next to the board.

    Returns:
        str: Token of the announcement.
    """
    return "".join(secrets.choice(TOKEN_ALPHABET) for _ in range(TOKEN_LENGTH))
