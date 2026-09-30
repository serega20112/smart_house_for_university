"""Static web interface of the smart home.

Serves the built frontend from the backend so the whole product runs from a
single process. Unknown paths fall back to the application shell, which is what
a client side router needs.
"""

from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles


REPO_ROOT = Path(__file__).resolve().parents[5]
FRONTEND_DIST = REPO_ROOT / "frontend" / "dist"
INDEX_FILE = "index.html"


def mount_frontend(app: FastAPI, dist: Path = FRONTEND_DIST) -> bool:
    """Serve the built interface from the root of the application.

    Args:
        app: Application to attach the interface to.
        dist: Directory holding the built frontend.

    Returns:
        bool: True when the interface was found and mounted.
    """
    if not (dist / INDEX_FILE).is_file():
        return False

    app.mount(
        "/assets",
        StaticFiles(directory=dist / "assets"),
        name="assets",
    )

    @app.get("/", include_in_schema=False)
    async def index() -> FileResponse:
        """Return the application shell.

        Returns:
            FileResponse: The built index page.
        """
        return FileResponse(dist / INDEX_FILE)

    @app.get("/{path:path}", include_in_schema=False)
    async def fallback(path: str) -> FileResponse:
        """Return a static file when it exists, the shell otherwise.

        Args:
            path: Requested path relative to the interface root.

        Returns:
            FileResponse: Static file or the application shell.
        """
        candidate = (dist / path).resolve()
        if candidate.is_file() and candidate.is_relative_to(dist.resolve()):
            return FileResponse(candidate)
        return FileResponse(dist / INDEX_FILE)

    return True
