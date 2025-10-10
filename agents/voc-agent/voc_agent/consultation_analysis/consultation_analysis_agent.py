"""상담 내용 분석 에이전트."""

from google.adk.agents.llm_agent import LlmAgent
from google.adk.models.lite_llm import LiteLlm

from ..prompts.consultation_analysis_prompt import CONSULTATION_ANALYSIS_PROMPT
from ..settings import settings

LLM_MODEL = LiteLlm(model=f"azure/{settings.azure_openai_deployment}")

consultation_analysis_agent = LlmAgent(
    name="consultation_analysis_agent",
    model=LLM_MODEL,
    instruction=CONSULTATION_ANALYSIS_PROMPT,
    tools=[],
)
