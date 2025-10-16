"""채팅 요약 에이전트를 정의하는 모듈"""

from __future__ import annotations

import asyncio
import os
from typing import Any

from dotenv import load_dotenv
from google.adk.agents.llm_agent import LlmAgent
from google.adk.models.lite_llm import LiteLlm
from google.adk.tools import BaseTool, ToolContext
from google.genai import types
from loguru import logger
from pydantic import BaseModel, Field, field_validator

from chat_analysis_agent.prompts import CONVERSATION_SUMMARY_PROMPT

load_dotenv()

AZURE_OPENAI_DEPLOYMENT = os.getenv("AZURE_OPENAI_DEPLOYMENT", "gpt-4o")
LLM_MODEL = LiteLlm(model=f"azure/{AZURE_OPENAI_DEPLOYMENT}", tool_choice="auto")


class ConfigureConversationSummaryContextArgs(BaseModel):
    """요약 컨텍스트 설정 도구 인자 모델."""

    text: str | None = Field(
        default=None,
        description="요약 대상이 되는 전체 상담 텍스트",
    )
    summary_type: str | None = Field(
        default=None,
        description="요약 방식(예: 기본 요약, 문제 위주 요약 등)",
    )
    max_bullet_count: int | None = Field(
        default=None,
        description="핵심 포인트 최대 개수 제한",
        ge=1,
    )

    @field_validator("text")
    @classmethod
    def _strip_text(cls, value: str | None) -> str | None:
        """텍스트 인자를 정제한다."""
        if isinstance(value, str):
            stripped = value.strip()
            return stripped if stripped else None
        return None


class ConfigureConversationSummaryContext(BaseTool):
    """채팅 요약을 위한 컨텍스트를 세션 상태에 반영하는 도구."""

    def __init__(self) -> None:
        """ConfigureConversationSummaryContext 도구를 초기화한다."""
        super().__init__(
            name="configure_conversation_summary_context",
            description="요약 작업에 필요한 텍스트와 제약 조건을 세션 상태에 저장하고 모델 안내 문구를 반환한다.",
        )

    def _get_declaration(self) -> types.FunctionDeclaration:
        """도구 선언 정보를 FunctionDeclaration 형식으로 반환한다.

        Returns:
            types.FunctionDeclaration: 요약 컨텍스트 설정 도구 정의.
        """
        schema_dict = ConfigureConversationSummaryContextArgs.model_json_schema()
        schema_dict.pop("title", None)
        return types.FunctionDeclaration(
            name=self.name,
            description=self.description,
            parameters=types.Schema.model_validate(schema_dict),
        )

    def run(self, *, args: dict[str, Any], tool_context: ToolContext) -> str:
        """도구를 동기적으로 실행하기 위한 헬퍼"""
        return asyncio.get_event_loop().run_until_complete(self.run_async(args=args, tool_context=tool_context))

    async def run_async(
        self,
        *,
        args: dict[str, Any],
        tool_context: ToolContext,
    ) -> str:
        """채팅 요약 컨텍스트를 설정하고 안내 문구를 생성한다.

        Args:
            args: 도구 호출 시 전달된 인자 사전.
            tool_context: 세션 상태와 동작을 제공하는 도구 컨텍스트.

        Returns:
            str: 요약 작업에 사용할 안내 문자열.
        """
        logger.info(f"ConfigureConversationSummaryContext called with args: {args}")

        parsed_args = ConfigureConversationSummaryContextArgs(**args)

        text = parsed_args.text or self._extract_conversation_text(tool_context)
        summary_type = parsed_args.summary_type
        max_bullet_count = parsed_args.max_bullet_count

        if text:
            tool_context.actions.state_delta.update({"user:summary_text": text})
            tool_context.state["user:summary_text"] = text

        if summary_type:
            normalized_summary_type = summary_type.strip()
            tool_context.actions.state_delta.update({"user:summary_type": normalized_summary_type})
            tool_context.state["user:summary_type"] = normalized_summary_type

        if max_bullet_count is not None:
            tool_context.actions.state_delta.update({"user:summary_max_bullet_count": max_bullet_count})
            tool_context.state["user:summary_max_bullet_count"] = max_bullet_count

        preview = (text or "")[:200] if text else "요약 대상 텍스트가 추후 제공됩니다."
        summary_type_display = summary_type or "기본 요약"
        bullet_display = f"최대 {max_bullet_count}개" if max_bullet_count else "제한 없음"

        return (
            "=== 요약 컨텍스트 ===\n"
            f"요약 종류: {summary_type_display}\n"
            f"핵심 포인트 개수 제한: {bullet_display}\n"
            f"텍스트 미리보기: {preview}\n"
            "===================="
        )

    @staticmethod
    def _extract_conversation_text(tool_context: ToolContext) -> str | None:
        """세션 상태에서 기존 대화 텍스트를 추출한다.

        Args:
            tool_context: 세션 상태를 포함한 도구 컨텍스트.

        Returns:
            Optional[str]: 저장된 대화 텍스트.
        """
        stored_text = tool_context.state.get("user:conversation_text")
        if isinstance(stored_text, str) and stored_text.strip():
            return stored_text
        return None


CONVERSATION_SUMMARY_AGENT = LlmAgent(
    name="conversation_summary_agent",
    model=LLM_MODEL,
    instruction=CONVERSATION_SUMMARY_PROMPT,
    tools=[ConfigureConversationSummaryContext()],
)


__all__ = [
    "ConfigureConversationSummaryContextArgs",
    "ConfigureConversationSummaryContext",
    "CONVERSATION_SUMMARY_AGENT",
]
