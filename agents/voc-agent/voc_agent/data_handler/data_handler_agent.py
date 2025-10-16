"""데이터 적재 워커 에이전트."""

from google.adk.agents.llm_agent import LlmAgent
from google.adk.models.lite_llm import LiteLlm
from google.adk.tools.mcp_tool.mcp_session_manager import SseConnectionParams
from google.adk.tools.mcp_tool.mcp_toolset import MCPToolset

from ..prompts.data_handler_prompt import prompt
from ..settings import settings

LLM_MODEL = LiteLlm(model=f"azure/{settings.azure_openai_deployment}")

DATA_HANDLER_MCP = MCPToolset(
    tool_filter=["insert_feedback_tool"],
    connection_params=SseConnectionParams(url=settings.stt_mcp_sse_url),
)

data_handler_agent = LlmAgent(
    name="data_handler_agent",
    model=LLM_MODEL,
    instruction=prompt.prompt,
    tools=[DATA_HANDLER_MCP],
    **prompt.config,
)
