import os
import warnings

import uvicorn
from a2a.types import AgentSkill
from dotenv import load_dotenv

from chat_analysis_agent.helpers import create_agent_a2a_server
from chat_analysis_agent.problem_resolution.problem_resolution_agent import PROBLEM_RESOLUTION_AGENT

load_dotenv()

warnings.filterwarnings("ignore", category=UserWarning)

PROBLEM_RESOLUTION_AGENT_PUBLIC_HOST = os.getenv("PROBLEM_RESOLUTION_AGENT_PUBLIC_HOST", "problem-resolution-agent")
PROBLEM_RESOLUTION_AGENT_PUBLIC_PORT = int(os.getenv("PROBLEM_RESOLUTION_AGENT_PUBLIC_PORT", "10003"))

app = create_agent_a2a_server(
    agent=PROBLEM_RESOLUTION_AGENT,
    name="Problem Resolution Evaluation Agent",
    description="Judge whether the customer issue has been resolved",
    version="0.1.0",
    skills=[
        AgentSkill(
            id="problem_resolution_agent",
            name="Problem Resolution Agent",
            description="Evaluate if a customer issue is resolved after the conversation",
            tags=["resolution", "analysis", "chat"],
            examples=[
                "Determine if the chatbot resolved the user's problem.",
            ],
        )
    ],
    public_host=PROBLEM_RESOLUTION_AGENT_PUBLIC_HOST,
    public_port=PROBLEM_RESOLUTION_AGENT_PUBLIC_PORT,
).build()

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=PROBLEM_RESOLUTION_AGENT_PUBLIC_PORT)  # nosec
