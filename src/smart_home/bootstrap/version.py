"""The version of the running build.

The number lives in ``pyproject.toml`` and nowhere else. The composition root
reads it from the metadata of the installed distribution and puts it into the
container, so a build installed from a tag and a build started from a checkout
report the same version and the health probe never disagrees with the packaging.
"""

from __future__ import annotations

from importlib.metadata import PackageNotFoundError, version

from smart_home.application.dto.version import ApplicationVersion

DISTRIBUTION_NAME = "smart-home-backend"
"""Name of the distribution the version is read from."""

FALLBACK_VERSION = "0.0.0"
"""Version reported when the distribution is not installed."""


def version_of() -> ApplicationVersion:
    """Return the version of the running build.

    Returns:
        ApplicationVersion: Version of the installed distribution, or a
        placeholder when the process runs from a checkout that was never
        installed.
    """
    try:
        return ApplicationVersion(version(DISTRIBUTION_NAME))
    except PackageNotFoundError:
        return ApplicationVersion(FALLBACK_VERSION)
