"""Helpers for building A2A server applications for ADK agents."""

from a2a.server.apps import A2AFastAPIApplication
from a2a.server.request_handlers import DefaultRequestHandler
from a2a.server.tasks import InMemoryTaskStore
from a2a.types import AgentCapabilities, AgentCard, AgentSkill
from core_common.logging import get_logger
from google.adk.a2a.executor.a2a_agent_executor import A2aAgentExecutor
from google.adk.agents import Agent
from google.adk.artifacts import InMemoryArtifactService
from google.adk.memory.in_memory_memory_service import InMemoryMemoryService
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService

from ..settings import settings

logger = get_logger(__name__)


def create_agent_a2a_server(
    agent: Agent,
    name: str,
    description: str,
    skills: list[AgentSkill],
    host: str | None = None,
    port: int | None = None,
) -> A2AFastAPIApplication:
    """Create an A2A server for any ADK agent."""

    resolved_host = host or settings.orchestrator_host
    resolved_port = port or settings.orchestrator_port

    capabilities = AgentCapabilities(streaming=True)

    agent_card = AgentCard(
        name=name,
        description=description,
        url=f"http://{resolved_host}:{resolved_port}/",
        version="1.0.0",
        default_input_modes=["text", "text/plain"],
        default_output_modes=["text", "text/plain"],
        capabilities=capabilities,
        skills=skills,
    )

    runner = Runner(
        app_name=agent_card.name,
        agent=agent,
        artifact_service=InMemoryArtifactService(),
        session_service=InMemorySessionService(),
        memory_service=InMemoryMemoryService(),
    )
    executor = A2aAgentExecutor(runner=runner)

    request_handler = DefaultRequestHandler(agent_executor=executor, task_store=InMemoryTaskStore())

    logger.debug(
        "A2A application created",
        extra={
            "agent_name": agent_card.name,
            "host": resolved_host,
            "port": resolved_port,
        },
    )

    return A2AFastAPIApplication(agent_card=agent_card, http_handler=request_handler)
