"""Entry point for running the diarization service."""

import uvicorn
from core_common.logging import get_logger

from ..settings import settings
from .diarization_server import app

logger = get_logger(__name__)


def main() -> None:
    """Launch the diarization server using uvicorn."""

    host = settings.diarization_host
    port = settings.diarization_port
    logger.info(
        "Starting dedicated diarization server",
        extra={"host": host, "port": port},
    )
    uvicorn.run(app, host=host, port=port)


if __name__ == "__main__":
    main()
