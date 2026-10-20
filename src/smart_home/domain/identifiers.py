"""Typed identifiers of every aggregate.

The domain owns identity. A surrogate integer handed out by the database is not an
identifier the model can reason about, so an aggregate is created with an
identifier that already exists and repositories never assign one afterwards.

Each aggregate gets a distinct type, which makes it impossible to pass a scenario
identifier where a device is expected, and the storage layer stores the very same
UUID instead of translating it into something else.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Self
from uuid import UUID, uuid4

from smart_home.domain.exceptions import MalformedIdentifierError


@dataclass(frozen=True, slots=True)
class UuidIdentifier:
    """Shared behaviour of every identifier of the model.

    Subclasses stay distinct types for the type checker while inheriting the
    generation and parsing rules, so the rules are written once.

    Args:
        value: Underlying UUID.

    Returns:
        None.

    Raises:
        MalformedIdentifierError: When the value is not a UUID.
    """

    value: UUID

    def __post_init__(self) -> None:
        """Validate the identifier.

        Returns:
            None.

        Raises:
            MalformedIdentifierError: When the value is not a UUID.
        """
        if not isinstance(self.value, UUID):
            raise MalformedIdentifierError(type(self).__name__, self.value)

    @classmethod
    def generate(cls) -> Self:
        """Produce an identifier that was never used before.

        Returns:
            Self: Fresh identifier.
        """
        return cls(uuid4())

    @classmethod
    def parse(cls, raw: str | UUID) -> Self:
        """Rebuild an identifier from its stored or transmitted form.

        Args:
            raw: UUID as text or as an already parsed UUID.

        Returns:
            Self: Parsed identifier.

        Raises:
            MalformedIdentifierError: When the text is not a UUID.
        """
        if isinstance(raw, UUID):
            return cls(raw)
        try:
            return cls(UUID(str(raw)))
        except (TypeError, ValueError) as error:
            raise MalformedIdentifierError(cls.__name__, raw) from error

    def __str__(self) -> str:
        """Return the canonical textual form of the identifier.

        Returns:
            str: UUID as lowercase hyphenated text.
        """
        return str(self.value)


@dataclass(frozen=True, slots=True)
class UserId(UuidIdentifier):
    """Identifier of one account."""


@dataclass(frozen=True, slots=True)
class DeviceId(UuidIdentifier):
    """Identifier of one logical device."""


@dataclass(frozen=True, slots=True)
class ScenarioId(UuidIdentifier):
    """Identifier of one timed scenario."""


@dataclass(frozen=True, slots=True)
class EspDeviceId(UuidIdentifier):
    """Identifier of one paired board."""


@dataclass(frozen=True, slots=True)
class EspClaimId(UuidIdentifier):
    """Identifier of one board announcement waiting for an owner."""
