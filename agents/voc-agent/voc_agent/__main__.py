"""Run the VOC agent orchestrator server."""

import os
from typing import Any

import uvicorn
from a2a.types import AgentSkill

from .create_agent_server import create_agent_a2a_server
from .orchestrator.orchestration_agent import orchestrator_agent

DEFAULT_HOST = os.getenv("VOC_AGENT_HOST", "127.0.0.1")
DEFAULT_PORT = int(os.getenv("VOC_AGENT_PORT", "10000"))

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


def build_app(host: str = DEFAULT_HOST, port: int = DEFAULT_PORT) -> Any:
    """Construct the FastAPI application for the orchestrator."""

    application = create_agent_a2a_server(
        agent=orchestrator_agent,
        name="VOC Analysis Pipeline Agent",
        description="Orchestrate STT processes from converting opus format to wav to diarize the given conversation",
        skills=[ORCHESTRATOR_SKILL],
        host=host,
        port=port,
    )
    return application.build()


def main() -> None:
    """Start the orchestrator server using uvicorn."""

    app = build_app()
    print(f"Starting VOC orchestrator server on {DEFAULT_HOST}:{DEFAULT_PORT}")
    uvicorn.run(app, host=DEFAULT_HOST, port=DEFAULT_PORT)


if __name__ == "__main__":
    main()
