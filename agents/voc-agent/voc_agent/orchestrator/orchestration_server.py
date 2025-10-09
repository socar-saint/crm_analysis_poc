"""Orchestration server."""

from a2a.types import AgentSkill

from ..settings import settings
from ..utils import create_agent_a2a_server
from .orchestration_agent import orchestrator_agent

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

app = create_agent_a2a_server(
    agent=orchestrator_agent,
    name="VOC Analysis Pipeline Agent",
    description="Orchestrate STT processes from converting opus format to wav to diarize the given conversation",
    skills=[ORCHESTRATOR_SKILL],
    host=settings.orchestrator_host,
    port=settings.orchestrator_port,
    public_host=settings.orchestrator_public_host,
).build()
