"""오케스트레이션 에이전트."""

import logging

from google.adk.agents.llm_agent import LlmAgent
from google.adk.agents.remote_a2a_agent import AGENT_CARD_WELL_KNOWN_PATH, RemoteA2aAgent
from google.adk.models.lite_llm import LiteLlm
from google.adk.tools import load_memory
from google.adk.tools.agent_tool import AgentTool

from ..prompts.orchestrator_prompt import prompt
from ..settings import settings
from ..utils.adk_patches import suppress_a2a_experimental_warnings

logging.getLogger("google_adk.google.adk.tools.base_authenticated_tool").setLevel(logging.ERROR)

# google-adk marks its A2A bridge as experimental; unwrap decorators so we avoid log spam.
suppress_a2a_experimental_warnings()

audio_processing_agent = RemoteA2aAgent(
    name="audio_processing_agent",
    description=(
        "Handle end-to-end audio processing: download audio from S3, convert formats, "
        "separate speakers, transcribe speech, and mask sensitive information"
    ),
    agent_card=f"{settings.audio_processing_base_url}/{AGENT_CARD_WELL_KNOWN_PATH}",
)

audio_processing_agent_tool = AgentTool(audio_processing_agent)

consultation_analysis_agent = RemoteA2aAgent(
    name="consultation_analysis_agent",
    description=(
        "Analyze consultation transcripts and produce structured insights, sentiment, "
        "and recommended follow-up actions"
    ),
    agent_card=f"{settings.consultation_analysis_base_url}/{AGENT_CARD_WELL_KNOWN_PATH}",
)

consultation_analysis_agent_tool = AgentTool(consultation_analysis_agent)

data_handler_agent = RemoteA2aAgent(
    name="data_handler_agent",
    description="Persist consultation analytics into the VOC database using MCP-backed tooling",
    agent_card=f"{settings.data_handler_base_url}/{AGENT_CARD_WELL_KNOWN_PATH}",
)

data_handler_agent_tool = AgentTool(data_handler_agent)

# Azure OpenAI 배포명(Deployment name)으로 LiteLlm 구성
AZURE_DEPLOYMENT = settings.azure_openai_deployment
LLM_MODEL = LiteLlm(model=f"azure/{AZURE_DEPLOYMENT}")


async def auto_save_session_to_memory_callback(callback_context):  # type: ignore
    """세션을 메모리에 저장하는 콜백."""
    await callback_context._invocation_context.memory_service.add_session_to_memory(
        callback_context._invocation_context.session
    )


orchestrator_agent = LlmAgent(
    name="orchestrator",
    model=LLM_MODEL,
    instruction=prompt.prompt,
    tools=[
        audio_processing_agent_tool,
        consultation_analysis_agent_tool,
        data_handler_agent_tool,
        load_memory,
    ],
    after_agent_callback=auto_save_session_to_memory_callback,
    **prompt.config,
)
