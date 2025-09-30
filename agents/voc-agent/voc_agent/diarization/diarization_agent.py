"""다이얼라이제이션 워커 에이전트."""

from google.adk.agents.llm_agent import LlmAgent
from google.adk.models.lite_llm import LiteLlm

from ..prompts.diarization_prompt import DIARIZATION_PROMPT
from ..settings import settings

LLM_MODEL = LiteLlm(model=f"azure/{settings.azure_openai_deployment}")

diarization_agent = LlmAgent(
    name="diarization_agent",
    model=LLM_MODEL,
    instruction=DIARIZATION_PROMPT,
)
