import os

from dotenv import load_dotenv
from google.adk.agents.llm_agent import LlmAgent
from google.adk.agents.remote_a2a_agent import (
    AGENT_CARD_WELL_KNOWN_PATH,
    RemoteA2aAgent,
)
from google.adk.models.lite_llm import LiteLlm
from google.adk.tools.agent_tool import AgentTool
from loguru import logger

from chat_analysis_agent.prompts import ORCHESTRATOR_PROMPT
from chat_analysis_agent.tools import LoadConversationFromCsvTool, MaskPiiTool

load_dotenv()

AZURE_DEPLOYMENT = os.getenv("AZURE_OPENAI_DEPLOYMENT", "gpt-4o")
LLM_MODEL = LiteLlm(model=f"azure/{AZURE_DEPLOYMENT}", tool_choice="auto")

SATISFACTION_EVALUATION_AGENT_URL = os.getenv("SATISFACTION_EVALUATION_AGENT_URL", "http://localhost:10001")
CONVERSATION_SUMMARY_AGENT_URL = os.getenv("CONVERSATION_SUMMARY_AGENT_URL", "http://localhost:10002")
PROBLEM_RESOLUTION_AGENT_URL = os.getenv("PROBLEM_RESOLUTION_AGENT_URL", "http://localhost:10003")

logger.info(f"SATISFACTION_EVALUATION_AGENT_URL: {SATISFACTION_EVALUATION_AGENT_URL}")
logger.info(f"CONVERSATION_SUMMARY_AGENT_URL: {CONVERSATION_SUMMARY_AGENT_URL}")
logger.info(f"PROBLEM_RESOLUTION_AGENT_URL: {PROBLEM_RESOLUTION_AGENT_URL}")

satisfaction_evaluation_agent = RemoteA2aAgent(
    name="satisfaction_evaluation_agent",
    description="Evaluate conversation satisfaction and emotions",
    agent_card=f"{SATISFACTION_EVALUATION_AGENT_URL}/{AGENT_CARD_WELL_KNOWN_PATH}",
)
satisfaction_evaluation_agent_tool = AgentTool(satisfaction_evaluation_agent)

conversation_summary_agent = RemoteA2aAgent(
    name="conversation_summary_agent",
    description="Summarize conversation transcripts into concise reports",
    agent_card=f"{CONVERSATION_SUMMARY_AGENT_URL}/{AGENT_CARD_WELL_KNOWN_PATH}",
)
conversation_summary_agent_tool = AgentTool(conversation_summary_agent)

problem_resolution_agent = RemoteA2aAgent(
    name="problem_resolution_agent",
    description="Judge whether the chatbot resolved the user's problem",
    agent_card=f"{PROBLEM_RESOLUTION_AGENT_URL}/{AGENT_CARD_WELL_KNOWN_PATH}",
)
problem_resolution_agent_tool = AgentTool(problem_resolution_agent)

ORCHESTRATOR_AGENT = LlmAgent(
    name="orchestration_agent",
    model=LLM_MODEL,
    instruction=ORCHESTRATOR_PROMPT,
    tools=[
        LoadConversationFromCsvTool(),
        MaskPiiTool(),
        conversation_summary_agent_tool,
        satisfaction_evaluation_agent_tool,
        problem_resolution_agent_tool,
    ],
)
