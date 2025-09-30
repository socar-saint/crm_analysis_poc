"""A2A 패턴을 따르는 예제 오케스트레이션 에이전트."""

from __future__ import annotations

from agent_common import A2ARequest, A2AResponse, get_logger

from .worker import ExampleWorkerAgent

logger = get_logger(__name__)


class ExampleOrchestratorAgent:
    """워크플로우를 정의하고 워커에게 작업을 위임."""

    def __init__(self, worker: ExampleWorkerAgent | None = None) -> None:
        """ExampleOrchestratorAgent 초기화"""
        self._worker = worker or ExampleWorkerAgent()
        logger.debug("ExampleOrchestratorAgent 초기화 완료")

    def plan_task(self, task: str) -> A2ARequest:
        """간단한 계획 수립 후 워커에게 전달할 요청을 만든다."""
        logger.info("작업 계획 수립: %s", task)
        return A2ARequest(task="example-task", payload={"instruction": task})

    def run(self, task: str) -> A2AResponse:
        """워커에게 작업을 위임하고 결과를 반환."""
        request = self.plan_task(task)
        response = self._worker.execute(request)
        logger.info("워커 응답 수신: %s", response.summary)
        return response
