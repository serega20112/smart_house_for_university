"""Shared mapping helpers used by every entity mapper."""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import Table

from backend.infrastructure.database.tables import Base


def row_values(table: Table, row: Base) -> dict[str, object]:
    """Return the column values of a row as a plain mapping.

    The repositories write through Core statements rather than through the object
    graph of the session, so a mapped instance has to be flattened first. Keeping
    that here means no repository has to know which columns a table happens to
    have.

    Args:
        table: Table the row belongs to.
        row: Row to flatten.

    Returns:
        dict[str, object]: Column name mapped to its value.
    """
    return {column.name: getattr(row, column.name) for column in table.columns}


def as_utc(value: datetime | None) -> datetime | None:
    """Return a datetime with UTC timezone, or None when the value is None."""
    if value is None:
        return None
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)


def parse_uuid(raw: str | UUID) -> UUID:
    """Parse a UUID value, raising on anything that is not a UUID."""
    if isinstance(raw, UUID):
        return raw
    return UUID(str(raw))
