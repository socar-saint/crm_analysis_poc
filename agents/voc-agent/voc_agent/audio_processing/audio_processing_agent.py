"""오디오 처리 워커 에이전트."""

from google.adk.agents.llm_agent import LlmAgent
from google.adk.models.lite_llm import LiteLlm
from google.adk.tools.mcp_tool.mcp_session_manager import SseConnectionParams
from google.adk.tools.mcp_tool.mcp_toolset import MCPToolset

from ..prompts.audio_processing_prompt import AUDIO_PROCESSING_PROMPT
from ..settings import settings

LLM_MODEL = LiteLlm(model=f"azure/{settings.azure_openai_deployment}")

AUDIO_PROCESSING_MCP = MCPToolset(
    connection_params=SseConnectionParams(url=settings.stt_mcp_sse_url),
)

audio_processing_agent = LlmAgent(
    name="audio_processing_agent",
    model=LLM_MODEL,
    instruction=AUDIO_PROCESSING_PROMPT,
    tools=[
        AUDIO_PROCESSING_MCP,
    ],
)
