"""A2A 워커 역할을 하는 간단한 예제."""

from __future__ import annotations

from agent_common import A2ARequest, A2AResponse, get_logger

logger = get_logger(__name__)


class ExampleWorkerAgent:
    """오케스트레이터가 보낸 요청을 처리."""

    def execute(self, request: A2ARequest) -> A2AResponse:
        """워커가 요청을 처리하고 결과를 반환."""
        logger.debug("워커 요청 수신: %s", request.payload)
        instruction = request.payload.get("instruction", "")
        completion = f"Instruction '{instruction}' processed by ExampleWorkerAgent."
        return A2AResponse(
            task=request.task,
            payload={"completion": completion},
            summary="예제 워커가 요청을 성공적으로 처리했습니다.",
        )
