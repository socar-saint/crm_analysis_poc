"""에이전트간(A2A) 통신에 사용하는 요청/응답 모델."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any


@dataclass(slots=True)
class A2ARequest:
    """오케스트레이션 에이전트가 워커에게 전달하는 표준 요청."""

    task: str
    payload: Mapping[str, Any]


@dataclass(slots=True)
class A2AResponse:
    """워커가 오케스트레이터에게 돌려주는 응답."""

    task: str
    payload: Mapping[str, Any]
    summary: str
