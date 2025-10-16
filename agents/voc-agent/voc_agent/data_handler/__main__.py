"""Entry point for running the data handler service."""

import uvicorn
from core_common.logging import get_logger

from ..settings import settings
from .data_handler_server import app

logger = get_logger(__name__)


def main() -> None:
    """Launch the data handler server using uvicorn."""

    host = settings.data_handler_host
    port = settings.data_handler_port
    logger.info(
        "Starting data handler server",
        extra={"host": host, "port": port},
    )
    uvicorn.run(app, host=host, port=port)


if __name__ == "__main__":
    main()
