"""Static web interface of the smart home.

Serves the built frontend from the backend so the whole product runs from a
single process and a single origin. Unknown paths fall back to the application
shell, which is what a client side router needs.

The location of the build is resolved from the environment first and then from
the layout of the image, so the same code runs from a checkout and from a
container without a rebuild.
"""

from __future__ import annotations

import os
from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

INDEX_FILE = "index.html"

CANDIDATES: tuple[Path, ...] = (
    Path("/frontend/dist"),
    Path(__file__).resolve().parents[5] / "frontend" / "dist",
    Path(__file__).resolve().parents[3] / "static",
)


def resolve_dist() -> Path | None:
    """Return the directory holding the built interface.

    Returns:
        Path | None: Directory with the build, or None when it is missing.
    """
    configured = os.getenv("FRONTEND_DIST")
    if configured:
        return Path(configured)
    for candidate in CANDIDATES:
        if (candidate / INDEX_FILE).is_file():
            return candidate
    return None


def mount_frontend(app: FastAPI, dist: Path | None = None) -> bool:
    """Serve the built interface from the root of the application.

    Args:
        app: Application to attach the interface to.
        dist: Directory holding the built frontend, resolved automatically when
            not given.

    Returns:
        bool: True when the interface was found and mounted.
    """
    directory = dist or resolve_dist()
    if directory is None or not (directory / INDEX_FILE).is_file():
        return False

    root = directory.resolve()
    app.mount("/assets", StaticFiles(directory=root / "assets"), name="assets")

    @app.get("/", include_in_schema=False)
    async def index() -> FileResponse:
        """Return the application shell.

        Returns:
            FileResponse: The built index page.
        """
        return FileResponse(root / INDEX_FILE)

    @app.get("/{path:path}", include_in_schema=False)
    async def fallback(path: str) -> FileResponse:
        """Return a static file when it exists, the shell otherwise.

        Args:
            path: Requested path relative to the interface root.

        Returns:
            FileResponse: Static file or the application shell.
        """
        candidate = (root / path).resolve()
        if candidate.is_file() and candidate.is_relative_to(root):
            return FileResponse(candidate)
        return FileResponse(root / INDEX_FILE)

    return True
