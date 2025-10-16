"""Data handler server."""

from a2a.types import AgentSkill

from ..settings import settings
from ..utils import create_agent_a2a_server
from .data_handler_agent import data_handler_agent

DATA_HANDLER_SKILL = AgentSkill(
    id="data_handler_agent",
    name="Data Handler Agent",
    description=(
        "Persist STT transcripts, summaries, categories, and anger scores "
        "into the VOC database via MCP. Include the full transcript text "
        "(`transcript_text`) and optionally the transcription JSON path "
        "(`transcript_file`) for validation."
    ),
    tags=["storage", "database", "stt", "summary"],
    examples=[
        (
            "Store this STT transcript with its summary and metadata. "
            "Use transcript_file=/app/downloads/transcriptions/...json."
        ),
        (
            "Record the consultation insights including anger score into the "
            "database, providing transcript_file when only the saved JSON path "
            "is available."
        ),
    ],
)

app = create_agent_a2a_server(
    agent=data_handler_agent,
    name="Data Handler Agent",
    description="Expose MCP-backed tools for persisting consultation analytics into the database.",
    skills=[DATA_HANDLER_SKILL],
    host=settings.data_handler_host,
    port=settings.data_handler_port,
    public_host=settings.data_handler_public_host,
).build()
