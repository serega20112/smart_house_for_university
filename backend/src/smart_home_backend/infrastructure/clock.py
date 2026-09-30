"""System clock adapter."""

from __future__ import annotations

from datetime import datetime, timezone

from smart_home_backend.application.interface.services import Clock


class SystemClock(Clock):
    """Clock reading the system time in UTC."""

    def now(self) -> datetime:
        """Return the current moment in UTC.

        Returns:
            datetime: Current moment.
        """
        return datetime.now(timezone.utc)
