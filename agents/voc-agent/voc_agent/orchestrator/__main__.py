"""Entry point for running the orchestration service."""

import uvicorn
from core_common.logging import get_logger

from ..settings import settings
from .orchestration_server import app

logger = get_logger(__name__)


def main() -> None:
    """Launch the orchestration server using uvicorn."""

    host = settings.orchestrator_host
    port = settings.orchestrator_port
    logger.info(
        "Starting dedicated orchestration server",
        extra={"host": host, "port": port},
    )
    uvicorn.run(app, host=host, port=port)


if __name__ == "__main__":
    main()
