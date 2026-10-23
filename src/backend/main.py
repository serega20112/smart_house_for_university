"""Entry point of the backend.

Starts uvicorn with the assembled application. The board connection, the
background loops and the Telegram bot run inside the application lifespan.
"""

from __future__ import annotations

import uvicorn

from backend.config import Settings
from backend.presentation.app_factory import create_app


def main() -> None:
    """Run the HTTP server.

    Returns:
        None.
    """
    settings = Settings()
    uvicorn.run(
        create_app(settings),
        host=settings.app_host,
        port=settings.app_port,
        log_level=settings.app_log_level.lower(),
    )


if __name__ == "__main__":
    main()
