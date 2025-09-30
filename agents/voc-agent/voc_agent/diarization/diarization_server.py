"""Diarization server."""

import uvicorn
from a2a.types import AgentSkill
from core_common.logging import get_logger
from google.adk.a2a.utils.agent_to_a2a import to_a2a

from ..settings import settings
from ..utils import create_agent_a2a_server
from .diarization_agent import diarization_agent

logger = get_logger(__name__)

app = create_agent_a2a_server(
    agent=diarization_agent,
    name="Diarization Agent",
    description="Diarize a given conversation between speakers",
    skills=[
        AgentSkill(
            id="diarization_agent",
            name="Diarization Agent",
            description="Diarize a given conversation between speakers",
            tags=["speakers", "dialog", "separation", "diarization"],
            examples=[
                "Diarize this conversation between two speakers.",
                "Separate two speakers conversation.",
            ],
        )
    ],
    host=settings.diarization_host,
    port=settings.diarization_port,
).build()

app_simple = to_a2a(diarization_agent)

if __name__ == "__main__":
    logger.info(
        "Starting dedicated diarization server",
        extra={"host": settings.diarization_host, "port": settings.diarization_port},
    )
    uvicorn.run(app, host=settings.diarization_host, port=settings.diarization_port)
