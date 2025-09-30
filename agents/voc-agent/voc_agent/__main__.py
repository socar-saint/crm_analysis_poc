"""Run the VOC agent orchestrator server."""

from typing import Any

import uvicorn
from a2a.types import AgentSkill
from core_common.logging import get_logger

from .orchestrator.orchestration_agent import orchestrator_agent
from .settings import settings
from .utils import create_agent_a2a_server

logger = get_logger(__name__)


ORCHESTRATOR_SKILL = AgentSkill(
    id="stt_orchestrator",
    name="VOC Analysis Pipeline Agent",
    description="Orchestrate STT processes from converting opus format to wav to diarize the given conversation",
    tags=["opus", "wav", "stt", "diarization"],
    examples=[
        "Convert the given voice file into diarized text without masking private information.",
        "Convert the given voice file into diarized text masking private information.",
    ],
)


def build_app(host: str | None = None, port: int | None = None) -> Any:
    """Construct the FastAPI application for the orchestrator."""

    resolved_host = host or settings.orchestrator_host
    resolved_port = port or settings.orchestrator_port
    logger.debug(
        "Building orchestrator app",
        extra={"host": resolved_host, "port": resolved_port},
    )

    application = create_agent_a2a_server(
        agent=orchestrator_agent,
        name="VOC Analysis Pipeline Agent",
        description="Orchestrate STT processes from converting opus format to wav to diarize the given conversation",
        skills=[ORCHESTRATOR_SKILL],
        host=resolved_host,
        port=resolved_port,
    )
    return application.build()


def main() -> None:
    """Start the orchestrator server using uvicorn."""

    app = build_app()
    host = settings.orchestrator_host
    port = settings.orchestrator_port
    logger.info("Starting VOC orchestrator server", extra={"host": host, "port": port})
    uvicorn.run(app, host=host, port=port)


if __name__ == "__main__":
    main()
