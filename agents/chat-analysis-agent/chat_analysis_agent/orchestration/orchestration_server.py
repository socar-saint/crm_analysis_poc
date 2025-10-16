import os
import warnings

import uvicorn
from a2a.types import AgentSkill
from dotenv import load_dotenv

from chat_analysis_agent.helpers import create_agent_a2a_server
from chat_analysis_agent.orchestration.orchestration_agent import ORCHESTRATOR_AGENT

load_dotenv()

warnings.filterwarnings("ignore", category=UserWarning)

ORCHESTRATOR_AGENT_PUBLIC_HOST = os.getenv("ORCHESTRATOR_AGENT_PUBLIC_HOST", "orchestration-agent")
ORCHESTRATOR_AGENT_PUBLIC_PORT = int(os.getenv("ORCHESTRATOR_AGENT_PUBLIC_PORT", "10000"))

# 오케스트레이션 에이전트 A2A 서버 생성
app = create_agent_a2a_server(
    agent=ORCHESTRATOR_AGENT,
    name="Orchestration Agent",
    description="Orchestrate the quality analysis of a given conversation",
    version="0.1.0",
    skills=[
        AgentSkill(
            id="orchestration_agent",
            name="Orchestration Agent",
            description="Orchestrate the quality analysis of a given conversation",
            tags=["orchestration", "quality", "chat"],
            examples=[
                "Evaluate the quality and sentiment of a given conversation.",
            ],
        )
    ],
    public_host=ORCHESTRATOR_AGENT_PUBLIC_HOST,
    public_port=ORCHESTRATOR_AGENT_PUBLIC_PORT,
).build()

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=ORCHESTRATOR_AGENT_PUBLIC_PORT)  # nosec
