"""System clock adapter.

The model never reads the clock, so every timestamp in the system arrives from
this one adapter. A test replaces it with a fixed implementation of
:class:`~smart_home.application.ports.services.Clock` instead of freezing time
globally.
"""

from __future__ import annotations

from datetime import UTC, datetime

from smart_home.application.ports.services import Clock


class SystemClock(Clock):
    """Clock reading the system time in UTC."""

    def now(self) -> datetime:
        """Return the current moment in UTC.

        Returns:
            datetime: Current moment.
        """
        return datetime.now(UTC)
