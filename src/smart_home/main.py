"""Entry point of the smart_home.

Starts uvicorn with the assembled application. The board connection, the
background loops and the Telegram bot run inside the application lifespan.
"""

from __future__ import annotations

import uvicorn

from smart_home.config import Settings
from smart_home.presentation.app_factory import create_app


def main() -> None:
    """Run the HTTP server.

    Returns:
        None.
    """
    settings = Settings()
    uvicorn.run(
        create_app(settings),
        host=settings.server.host,
        port=settings.server.port,
        log_level=settings.server.log_level.lower(),
    )


if __name__ == "__main__":
    main()
