"""Diarization server."""

from a2a.types import AgentSkill

from ..settings import settings
from ..utils import create_agent_a2a_server
from .diarization_agent import diarization_agent

DIARIZATION_SKILL = AgentSkill(
    id="diarization_agent",
    name="Diarization Agent",
    description="Diarize a given conversation between speakers",
    tags=["speakers", "dialog", "separation", "diarization"],
    examples=[
        "Diarize this conversation between two speakers.",
        "Separate two speakers conversation.",
    ],
)

app = create_agent_a2a_server(
    agent=diarization_agent,
    name="Diarization Agent",
    description="Diarize a given conversation between speakers",
    skills=[
        DIARIZATION_SKILL,
    ],
    host=settings.diarization_host,
    port=settings.diarization_port,
    public_host=settings.diarization_public_host,
).build()
