"""Password hashing.

The stored form is self describing: it names the algorithm, the iteration count
and the salt that produced it, so the cost can be raised later without a
migration of the existing rows. Verification compares digests in constant time.
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import secrets

from smart_home.application.ports.services import PasswordHasher

ALGORITHM = "pbkdf2_sha256"
DEFAULT_ITERATIONS = 600_000
DEFAULT_SALT_BYTES = 16
DIGEST = "sha256"
FIELD_SEPARATOR = "$"
SALT_BYTES_ENCODED = 22
DIGEST_BYTES_ENCODED = 43


class Pbkdf2PasswordHasher(PasswordHasher):
    """Derives stored passwords with PBKDF2-HMAC-SHA256.

    Args:
        iterations: Stretching rounds of one derivation. A higher number costs
            linearly more time and only ever applies to freshly stored passwords.
        salt_bytes: Length of the per password salt.
        digest: Name of the hash used inside PBKDF2.

    Returns:
        None.
    """

    def __init__(
        self,
        iterations: int = DEFAULT_ITERATIONS,
        salt_bytes: int = DEFAULT_SALT_BYTES,
        digest: str = DIGEST,
    ) -> None:
        """Initialize the hasher.

        Args:
            iterations: Stretching rounds of one derivation.
            salt_bytes: Length of the per password salt.
            digest: Name of the hash used inside PBKDF2.

        Returns:
            None.
        """
        self._iterations = iterations
        self._salt_bytes = salt_bytes
        self._digest = digest

    def hash(self, password: str) -> str:
        """Produce the stored form of a password.

        Args:
            password: Plain password chosen by the user.

        Returns:
            str: Self describing stored form carrying the salt and the cost.
        """
        salt = secrets.token_bytes(self._salt_bytes)
        digest = hashlib.pbkdf2_hmac(
            self._digest, password.encode("utf-8"), salt, self._iterations, dklen=32
        )
        return FIELD_SEPARATOR.join(
            (
                ALGORITHM,
                str(self._iterations),
                _encode(salt),
                _encode(digest),
            )
        )

    def verify(self, password: str, stored: str) -> bool:
        """Check a plain password against a stored one.

        A stored form this hasher does not understand is refused rather than
        parsed leniently, because a lenient parser turns a corrupted row into a
        successful login.

        Args:
            password: Plain password to check.
            stored: Stored form produced by :meth:`hash`.

        Returns:
            bool: True when the password matches.
        """
        algorithm, iterations, salt, expected = _split(stored)
        if algorithm != ALGORITHM:
            return False
        digest = hashlib.pbkdf2_hmac(
            self._digest, password.encode("utf-8"), salt, iterations, dklen=32
        )
        return hmac.compare_digest(digest, expected)


def _split(stored: str) -> tuple[str, int, bytes, bytes]:
    parts = stored.split(FIELD_SEPARATOR)
    if len(parts) != 4:
        raise ValueError("stored password is not a self describing PBKDF2 form")
    algorithm, raw_iterations, raw_salt, raw_digest = parts
    return algorithm, int(raw_iterations), _decode(raw_salt), _decode(raw_digest)


def _encode(raw: bytes) -> str:
    return base64.urlsafe_b64encode(raw).decode("ascii").rstrip("=")


def _decode(value: str) -> bytes:
    padding = "=" * (-len(value) % 4)
    return base64.urlsafe_b64decode(value + padding)
