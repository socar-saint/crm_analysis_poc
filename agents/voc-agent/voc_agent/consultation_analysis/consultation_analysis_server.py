"""Consultation analysis server."""

from a2a.types import AgentSkill

from ..settings import settings
from ..utils import create_agent_a2a_server
from .consultation_analysis_agent import consultation_analysis_agent

CONSULTATION_ANALYSIS_SKILL = AgentSkill(
    id="consultation_analysis_agent",
    name="Consultation Analysis Agent",
    description="Analyze consultation transcripts to extract insights and structured summaries.",
    tags=["consultation", "analysis", "summary", "insights"],
    examples=[
        "Review this counseling transcript and highlight key issues and sentiment.",
        "Analyze the consultation notes and suggest follow-up actions.",
    ],
)

app = create_agent_a2a_server(
    agent=consultation_analysis_agent,
    name="Consultation Analysis Agent",
    description="Provide structured analysis of consultation transcripts and related artifacts.",
    skills=[CONSULTATION_ANALYSIS_SKILL],
    host=settings.consultation_analysis_host,
    port=settings.consultation_analysis_port,
    public_host=settings.consultation_analysis_public_host,
).build()
