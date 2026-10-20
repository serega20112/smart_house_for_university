"""Shared behaviour of every unit of work.

The transaction protocol lives here once: enter the block, commit when nothing
raised, roll back when something did. The concrete units of work add nothing but
the repositories they expose, which is what keeps three small classes instead of
three copies of the same lifecycle.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from types import TracebackType
from typing import Self


class TransactionalUnitOfWork(ABC):
    """A block of work that ends in exactly one commit or one rollback."""

    async def __aenter__(self) -> Self:
        """Open the transaction.

        Returns:
            Self: Unit of work for use inside the with block.
        """
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> bool:
        """Commit on success and roll back on failure.

        Args:
            exc_type: Raised exception type or None.
            exc_val: Raised exception value or None.
            exc_tb: Raised exception traceback or None.

        Returns:
            bool: False so exceptions keep propagating.
        """
        if exc_type is None:
            await self.commit()
        else:
            await self.rollback()
        return False

    @abstractmethod
    async def commit(self) -> None:
        """Persist everything done inside the block atomically.

        Returns:
            None.
        """

    @abstractmethod
    async def rollback(self) -> None:
        """Discard everything done inside the block.

        Returns:
            None.
        """
