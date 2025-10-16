import os
import warnings

import uvicorn
from a2a.types import AgentSkill
from dotenv import load_dotenv

from chat_analysis_agent.conversation_summary.conversation_summary_agent import CONVERSATION_SUMMARY_AGENT
from chat_analysis_agent.helpers import create_agent_a2a_server

load_dotenv()

warnings.filterwarnings("ignore", category=UserWarning)

CONVERSATION_SUMMARY_AGENT_PUBLIC_HOST = os.getenv(
    "CONVERSATION_SUMMARY_AGENT_PUBLIC_HOST", "conversation-summary-agent"
)
CONVERSATION_SUMMARY_AGENT_PUBLIC_PORT = int(os.getenv("CONVERSATION_SUMMARY_AGENT_PUBLIC_PORT", "10002"))


# 채팅 요약 에이전트 A2A 서버 생성
app = create_agent_a2a_server(
    agent=CONVERSATION_SUMMARY_AGENT,
    name="Conversation Summary Agent",
    description="Summarize conversation transcripts into concise reports",
    version="0.1.0",
    skills=[
        AgentSkill(
            id="conversation_summary_agent",
            name="Conversation Summary Agent",
            description="Summarize conversation transcripts into concise reports",
            tags=["summary", "chat", "analysis"],
            examples=[
                "Summarize a conversation and extract key points.",
            ],
        )
    ],
    public_host=CONVERSATION_SUMMARY_AGENT_PUBLIC_HOST,
    public_port=CONVERSATION_SUMMARY_AGENT_PUBLIC_PORT,
).build()

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=CONVERSATION_SUMMARY_AGENT_PUBLIC_PORT)  # nosec
