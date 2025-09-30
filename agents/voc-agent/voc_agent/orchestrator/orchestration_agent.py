"""VOC 오케스트레이션 에이전트 구현."""

from __future__ import annotations

from typing import Protocol

from agent_common import A2ARequest, A2AResponse, get_logger

logger = get_logger(__name__)


class DiarizationWorker(Protocol):
    """다이얼라이제이션 워커가 제공해야 하는 인터페이스."""

    def diarize(self, request: A2ARequest) -> A2AResponse:
        """다이얼라이제이션 작업을 처리."""
        ...


class VocOrchestrationAgent:
    """다이얼라이제이션 워커를 조율하여 VOC 태스크를 처리."""

    def __init__(self, diarization_worker: DiarizationWorker) -> None:
        """VocOrchestrationAgent 초기화"""
        self._diarization_worker = diarization_worker
        logger.debug("VocOrchestrationAgent 초기화 완료")

    def handle_request(self, audio_uri: str) -> A2AResponse:
        """오디오 파일을 받아 워커에게 A2A 요청을 위임."""
        logger.info("다이얼라이제이션 작업 위임: %s", audio_uri)
        request = A2ARequest(task="diarization", payload={"audio_uri": audio_uri})
        response = self._diarization_worker.diarize(request)
        logger.info("다이얼라이제이션 완료: %s", response.summary)
        return response
