"""The version of the running build as the interface sees it."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class ApplicationVersion:
    """Version of the build the process runs.

    Attributes:
        value: Version of the installed distribution.

    """

    value: str
