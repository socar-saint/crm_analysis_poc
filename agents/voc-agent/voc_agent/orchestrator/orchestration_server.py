"""Orchestration server."""

from a2a.types import AgentSkill

from ..settings import settings
from ..utils import create_agent_a2a_server
from .orchestration_agent import orchestrator_agent

ORCHESTRATOR_SKILL = AgentSkill(
    id="stt_orchestrator",
    name="VOC Analysis Pipeline Agent",
    description=(
        "Coordinate audio conversion, diarization, consultation analysis, and persistence of structured results."
    ),
    tags=["opus", "wav", "stt", "diarization", "analysis", "storage"],
    examples=[
        "Process this call from download to persistent storage with diarized, masked transcripts.",
        "Analyze the consultation and store the summary, category, and anger score in the database.",
    ],
)

app = create_agent_a2a_server(
    agent=orchestrator_agent,
    name="VOC Analysis Pipeline Agent",
    description=(
        "Coordinate audio conversion, diarization, consultation analysis, and persistence of structured results."
    ),
    skills=[ORCHESTRATOR_SKILL],
    host=settings.orchestrator_host,
    port=settings.orchestrator_port,
    public_host=settings.orchestrator_public_host,
).build()
