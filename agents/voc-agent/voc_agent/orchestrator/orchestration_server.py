"""Orchestration server."""

import uvicorn
from a2a.types import AgentSkill
from google.adk.a2a.utils.agent_to_a2a import to_a2a

from ..create_agent_server import create_agent_a2a_server
from .orchestration_agent import orchestrator_agent

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
    host="127.0.0.1",
    port=10000,
).build()

# ADK의 Agent서빙을 위한 helper 함수인데 A2A 수행중 agent card를 제대로 가져오지 못하거나 프로토콜 에러가 발생됨.
app_simple = to_a2a(orchestrator_agent)

if __name__ == "__main__":
    uvicorn.run(app, port=10000)
