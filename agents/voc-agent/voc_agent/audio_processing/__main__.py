"""Entry point for running the audio processing service."""

import uvicorn
from core_common.logging import get_logger

from ..settings import settings
from .audio_processing_server import app

logger = get_logger(__name__)


def main() -> None:
    """Launch the audio processing server using uvicorn."""

    host = settings.audio_processing_host
    port = settings.audio_processing_port
    logger.info(
        "Starting dedicated audio processing server",
        extra={"host": host, "port": port},
    )
    uvicorn.run(app, host=host, port=port)


if __name__ == "__main__":
    main()
