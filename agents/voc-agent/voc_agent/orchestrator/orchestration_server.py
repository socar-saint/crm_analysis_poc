"""Orchestration server."""

import uvicorn
from a2a.types import AgentSkill
from core_common.logging import get_logger

from ..settings import settings
from ..utils import create_agent_a2a_server
from .orchestration_agent import orchestrator_agent

logger = get_logger(__name__)

app = create_agent_a2a_server(
    agent=orchestrator_agent,
    name="VOC Analysis Pipeline Agent",
    description="Orchestrate STT processes from converting opus format to wav to diarize the given conversation",
    skills=[
        AgentSkill(
            id="stt_orchestartor",
            name="VOC Analysis Pipeline Agent",
            description=(
                "Orchestrate STT processes from converting opus format to wav to diarize the given conversation"
            ),
            tags=["opus", "wav", "stt", "diarization"],
            examples=[
                "Convert the given voice file into diarized text without masking private information.",
                "Convert the given voice file into diarized text masking private information.",
            ],
        )
    ],
    host=settings.orchestrator_host,
    port=settings.orchestrator_port,
).build()

if __name__ == "__main__":
    logger.info(
        "Starting dedicated orchestration server",
        extra={"host": settings.orchestrator_host, "port": settings.orchestrator_port},
    )
    uvicorn.run(app, host=settings.orchestrator_host, port=settings.orchestrator_port)
