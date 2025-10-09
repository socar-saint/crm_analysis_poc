"""오케스트레이션 에이전트."""

import logging

from google.adk.agents.llm_agent import LlmAgent
from google.adk.agents.remote_a2a_agent import AGENT_CARD_WELL_KNOWN_PATH, RemoteA2aAgent
from google.adk.models.lite_llm import LiteLlm
from google.adk.tools.agent_tool import AgentTool
from google.adk.tools.mcp_tool.mcp_session_manager import SseConnectionParams
from google.adk.tools.mcp_tool.mcp_toolset import MCPToolset

from ..prompts.orchestrator_prompt import ORCHESTRATOR_PROMPT
from ..settings import settings

logging.getLogger("google_adk.google.adk.tools.base_authenticated_tool").setLevel(logging.ERROR)

diarization_agent = RemoteA2aAgent(
    name="diarization_agent",
    description="Diarize a given conversation between speakers",
    agent_card=f"{settings.diarization_base_url}/{AGENT_CARD_WELL_KNOWN_PATH}",
)

diarization_agent_tool = AgentTool(diarization_agent)


stt_mcp = MCPToolset(
    connection_params=SseConnectionParams(url=settings.stt_mcp_sse_url),
)

# Azure OpenAI 배포명(Deployment name)으로 LiteLlm 구성
AZURE_DEPLOYMENT = settings.azure_openai_deployment
LLM_MODEL = LiteLlm(model=f"azure/{AZURE_DEPLOYMENT}")

orchestrator_agent = LlmAgent(
    name="orchestrator",
    model=LLM_MODEL,
    instruction=ORCHESTRATOR_PROMPT,
    tools=[
        stt_mcp,
        diarization_agent_tool,
    ],
)
