"""Diarization server."""

import uvicorn
from a2a.types import AgentSkill
from google.adk.a2a.utils.agent_to_a2a import to_a2a

from ..create_agent_server import create_agent_a2a_server
from .diarization_agent import diarization_agent

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
    host="127.0.0.1",
    port=10001,
).build()

app_simple = to_a2a(diarization_agent)

if __name__ == "__main__":
    uvicorn.run(app, port=10001)
