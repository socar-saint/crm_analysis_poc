"""VOC 다이얼라이제이션 워커 에이전트."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from agent_common import A2ARequest, A2AResponse, get_logger

logger = get_logger(__name__)


class VocDiarizationAgent:
    """오디오 파일을 단순히 더미 스피커 분리 결과로 변환."""

    def diarize(self, request: A2ARequest) -> A2AResponse:
        """오디오 파일을 단순히 더미 스피커 분리 결과로 변환."""
        logger.debug("다이얼라이제이션 요청 수신: %s", request.payload)
        audio_uri = request.payload.get("audio_uri", "unknown")
        segments: list[Mapping[str, Any]] = [
            {"speaker": "customer", "start": 0.0, "end": 5.2},
            {"speaker": "agent", "start": 5.2, "end": 10.8},
        ]
        summary = f"{audio_uri} 에 대해 {len(segments)}개 화자 세그먼트를 생성했습니다."
        return A2AResponse(task=request.task, payload={"segments": segments}, summary=summary)
