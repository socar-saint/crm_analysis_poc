"""문제 해결 여부 판단 에이전트를 정의하는 모듈."""

from __future__ import annotations

import asyncio
import os
from collections.abc import Sequence
from typing import Any

from dotenv import load_dotenv
from google.adk.agents.llm_agent import LlmAgent
from google.adk.models.lite_llm import LiteLlm
from google.adk.tools import BaseTool, ToolContext
from google.genai import types
from loguru import logger
from pydantic import BaseModel, Field

from chat_analysis_agent.prompts import PROBLEM_RESOLUTION_EVALUATION_PROMPT

load_dotenv()

AZURE_OPENAI_DEPLOYMENT = os.getenv("AZURE_OPENAI_DEPLOYMENT", "gpt-4o")
LLM_MODEL = LiteLlm(model=f"azure/{AZURE_OPENAI_DEPLOYMENT}", tool_choice="auto")


class ConfigureProblemResolutionContextArgs(BaseModel):
    """문제 해결 판단 도구 인자 모델."""

    text: str | None = Field(
        default=None,
        description="판단 대상 전체 상담 텍스트",
    )
    allowed_resolution_statuses: list[str] | None = Field(
        default=None,
        description="허용된 해결 상태 라벨 목록",
    )
    include_next_steps: bool | None = Field(
        default=None,
        description="후속 조치 목록 포함 여부",
    )


class ConfigureProblemResolutionContext(BaseTool):
    """문제 해결 여부 판단을 위한 컨텍스트를 세션 상태에 반영하는 도구."""

    def __init__(self) -> None:
        """ConfigureProblemResolutionContext 도구를 초기화한다."""
        super().__init__(
            name="configure_problem_resolution_context",
            description="문제 해결 판단에 필요한 텍스트와 라벨 제약을 세션 상태에 저장하고 모델 안내 문구를 반환한다.",
        )

    def _get_declaration(self) -> types.FunctionDeclaration:
        """도구 선언 정보를 FunctionDeclaration 형식으로 반환한다.

        Returns:
            types.FunctionDeclaration: 문제 해결 판단 도구 정의.
        """
        schema_dict = ConfigureProblemResolutionContextArgs.model_json_schema()
        schema_dict.pop("title", None)
        return types.FunctionDeclaration(
            name=self.name,
            description=self.description,
            parameters=types.Schema.model_validate(schema_dict),
        )

    def run(self, *, args: dict[str, Any], tool_context: ToolContext) -> str:
        """도구를 동기적으로 실행하기 위한 헬퍼."""
        return asyncio.get_event_loop().run_until_complete(self.run_async(args=args, tool_context=tool_context))

    async def run_async(
        self,
        *,
        args: dict[str, Any],
        tool_context: ToolContext,
    ) -> str:
        """문제 해결 판단 컨텍스트를 설정하고 안내 문구를 생성한다.

        Args:
            args: 도구 호출 시 전달된 인자 사전.
            tool_context: 세션 상태와 동작을 제공하는 도구 컨텍스트.

        Returns:
            str: 문제 해결 판단에 사용할 안내 문자열.
        """
        logger.info(f"ConfigureProblemResolutionContext called with args: {args}")

        parsed_args = ConfigureProblemResolutionContextArgs(**args)

        text = self._normalize_text(
            parsed_args.text,
            fallback=tool_context.state.get("user:conversation_text"),
        )
        allowed_statuses = self._normalize_statuses(parsed_args.allowed_resolution_statuses)
        include_next_steps = (
            bool(parsed_args.include_next_steps) if parsed_args.include_next_steps is not None else False
        )

        if text:
            tool_context.actions.state_delta.update({"user:resolution_text": text})
            tool_context.state["user:resolution_text"] = text

        tool_context.actions.state_delta.update({"user:include_next_steps": include_next_steps})
        tool_context.state["user:include_next_steps"] = include_next_steps

        if allowed_statuses:
            tool_context.actions.state_delta.update({"user:allowed_resolution_statuses": allowed_statuses})
            tool_context.state["user:allowed_resolution_statuses"] = allowed_statuses

        preview = text[:200] if text else "판단 대상 텍스트가 추후 제공됩니다."
        status_display = (
            ", ".join(allowed_statuses) if allowed_statuses else "resolved, partially_resolved, unresolved"
        )
        next_steps_display = "포함" if include_next_steps else "생략"

        return (
            "=== 문제 해결 판단 컨텍스트 ===\n"
            f"허용 해결 상태: {status_display}\n"
            f"다음 조치 작성: {next_steps_display}\n"
            f"텍스트 미리보기: {preview}\n"
            "============================="
        )

    @staticmethod
    def _normalize_text(candidate: str | None, fallback: str | None) -> str | None:
        """텍스트 인자를 정제하고 fallback을 고려해 선택한다.

        Args:
            candidate: 도구 인자로 전달된 텍스트.
            fallback: 세션 상태에 저장된 대체 텍스트.

        Returns:
            Optional[str]: 사용 가능한 정제된 텍스트.
        """
        if isinstance(candidate, str):
            stripped_candidate = candidate.strip()
            if stripped_candidate:
                return stripped_candidate
        if isinstance(fallback, str):
            stripped_fallback = fallback.strip()
            if stripped_fallback:
                return stripped_fallback
        return None

    @staticmethod
    def _normalize_statuses(statuses: Sequence[str] | None) -> list[str]:
        """허용된 해결 상태 목록을 정제한다.

        Args:
            statuses: 문자열 목록 혹은 None.

        Returns:
            List[str]: 공백이 제거된 해결 상태 목록.
        """
        normalized: list[str] = []
        if statuses:
            for status in statuses:
                if isinstance(status, str):
                    stripped = status.strip()
                    if stripped:
                        normalized.append(stripped)
        return normalized


PROBLEM_RESOLUTION_AGENT = LlmAgent(
    name="problem_resolution_agent",
    model=LLM_MODEL,
    instruction=PROBLEM_RESOLUTION_EVALUATION_PROMPT,
    tools=[ConfigureProblemResolutionContext()],
)


__all__ = [
    "ConfigureProblemResolutionContextArgs",
    "ConfigureProblemResolutionContext",
    "PROBLEM_RESOLUTION_AGENT",
]
