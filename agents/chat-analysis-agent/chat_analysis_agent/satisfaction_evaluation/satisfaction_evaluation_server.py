import os
import warnings

import uvicorn
from a2a.types import AgentSkill
from dotenv import load_dotenv

from chat_analysis_agent.helpers import create_agent_a2a_server
from chat_analysis_agent.satisfaction_evaluation.satisfaction_evaluation_agent import (
    SATISFACTION_EVALUATION_AGENT,
)

load_dotenv()

warnings.filterwarnings("ignore", category=UserWarning)

SATISFACTION_EVALUATION_AGENT_PUBLIC_HOST = os.getenv(
    "SATISFACTION_EVALUATION_AGENT_PUBLIC_HOST", "satisfaction-evaluation-agent"
)
SATISFACTION_EVALUATION_AGENT_PUBLIC_PORT = int(os.getenv("SATISFACTION_EVALUATION_AGENT_PUBLIC_PORT", "10001"))

# 채팅 만족도 평가 에이전트 A2A 서버 생성
app = create_agent_a2a_server(
    agent=SATISFACTION_EVALUATION_AGENT,
    name="Satisfaction Evaluation Agent",
    description="Evaluate conversation satisfaction and emotions",
    version="0.1.0",
    skills=[
        AgentSkill(
            id="satisfaction_evaluation_agent",
            name="Satisfaction Evaluation Agent",
            description="Evaluate conversation satisfaction and emotions",
            tags=["satisfaction", "emotion", "chat"],
            examples=[
                "Evaluate satisfaction and emotion for a conversation.",
            ],
        )
    ],
    public_host=SATISFACTION_EVALUATION_AGENT_PUBLIC_HOST,
    public_port=SATISFACTION_EVALUATION_AGENT_PUBLIC_PORT,
).build()

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=SATISFACTION_EVALUATION_AGENT_PUBLIC_PORT)  # nosec
