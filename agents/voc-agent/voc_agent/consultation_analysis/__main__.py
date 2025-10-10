"""Entry point for running the consultation analysis service."""

import uvicorn
from core_common.logging import get_logger

from ..settings import settings
from .consultation_analysis_server import app

logger = get_logger(__name__)


def main() -> None:
    """Launch the consultation analysis server using uvicorn."""

    host = settings.consultation_analysis_host
    port = settings.consultation_analysis_port
    logger.info(
        "Starting consultation analysis server",
        extra={"host": host, "port": port},
    )
    uvicorn.run(app, host=host, port=port)


if __name__ == "__main__":
    main()
