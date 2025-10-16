from collections.abc import Sequence

from a2a.server.apps import A2AFastAPIApplication
from a2a.server.request_handlers import DefaultRequestHandler
from a2a.server.tasks import InMemoryTaskStore
from a2a.types import (
    AgentCapabilities,
    AgentCard,
    AgentSkill,
)
from google.adk import Agent
from google.adk.a2a.executor.a2a_agent_executor import A2aAgentExecutor
from google.adk.artifacts import InMemoryArtifactService
from google.adk.memory.in_memory_memory_service import InMemoryMemoryService
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from loguru import logger


def create_agent_a2a_server(
    agent: Agent,
    name: str,
    description: str,
    version: str,
    skills: Sequence[AgentSkill],
    public_host: str,
    public_port: int,
) -> A2AFastAPIApplication:
    """ADK 에이전트에 대한 A2A 서버를 생성한다.

    Args:
        agent: ADK 에이전트 인스턴스
        name: 에이전트 표시 이름
        description: 에이전트 설명
        version: 에이전트 버전
        skills: AgentSkill 객체 리스트
        public_host: Agent card에 노출될 공개 서버 호스트
        public_port: Agent card에 노출될 공개 서버 포트
    """
    capabilities = AgentCapabilities(streaming=True)

    agent_card_url = f"http://{public_host}:{public_port}/"
    logger.info(f"Agent card for {name} is created at URL: {agent_card_url}")

    agent_card = AgentCard(
        name=name,
        description=description,
        url=agent_card_url,
        version=version,
        defaultInputModes=["text", "text/plain"],
        defaultOutputModes=["text", "text/plain"],
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

    return A2AFastAPIApplication(agent_card=agent_card, http_handler=request_handler)
