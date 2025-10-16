"""google-adk LlmAgent 패턴을 활용한 만족도 평가 에이전트 정의 모듈입니다."""

import asyncio
import os
from collections.abc import Sequence
from typing import Any, cast

from dotenv import load_dotenv
from google.adk.agents.llm_agent import LlmAgent
from google.adk.models.lite_llm import LiteLlm
from google.adk.tools import BaseTool, ToolContext
from google.genai import types
from loguru import logger
from pydantic import BaseModel, Field

from chat_analysis_agent.prompts import SATISFACTION_EVALUATION_PROMPT

load_dotenv()

AZURE_OPENAI_DEPLOYMENT = os.getenv("AZURE_OPENAI_DEPLOYMENT")
LLM_MODEL = LiteLlm(model=f"azure/{AZURE_OPENAI_DEPLOYMENT}", tool_choice="auto")


class ConfigureSatisfactionEvaluationContextArgs(BaseModel):
    """만족도 평가 도구 호출 인자 모델."""

    text: str | None = Field(
        default=None,
        description="평가할 텍스트",
    )
    allowed_emotions: list[str] | None = Field(
        default=None,
        description="허용된 감정 목록",
    )
    allowed_satisfactions: list[str] | None = Field(
        default=None,
        description="허용된 만족도 등급 목록",
    )
    evaluation_aspect: str | None = Field(
        default=None,
        description="평가할 서비스 측면(친절함, 속도 등)",
    )


class ConfigureSatisfactionEvaluationContext(BaseTool):
    """채팅 로그에 대한 만족도 평가 컨텍스트를 세션 상태에 반영하는 도구."""

    def __init__(self) -> None:
        """ConfigureSatisfactionEvaluationContext 도구를 초기화한다."""
        super().__init__(
            name="configure_satisfaction_context",
            description=(
                "만족도 평가에 필요한 라벨과 대상 텍스트 정보를 세션 상태에 저장하고, "
                "모델이 참고할 수 있는 안내 문구를 반환한다."
            ),
        )

    def _get_declaration(self) -> types.FunctionDeclaration:
        """도구 스키마를 FunctionDeclaration 형식으로 반환한다.

        Returns:
            types.FunctionDeclaration: 만족도 평가 도구 정의.
        """
        schema_dict = ConfigureSatisfactionEvaluationContextArgs.model_json_schema()
        schema_dict.pop("title", None)
        return types.FunctionDeclaration(
            name=self.name,
            description=self.description,
            parameters=types.Schema.model_validate(schema_dict),
        )

    def run(self, *, args: dict[str, Any], tool_context: ToolContext) -> str:
        """도구를 동기적으로 실행하기 위한 래퍼 메서드."""
        return asyncio.get_event_loop().run_until_complete(self.run_async(args=args, tool_context=tool_context))

    async def run_async(
        self,
        *,
        args: dict[str, Any],
        tool_context: ToolContext,
    ) -> str:
        """채팅 로그에 대한 만족도 평가 컨텍스트를 설정하고 안내 문구를 반환한다.

        Args:
            args: 도구 호출 시 전달된 인자 사전.
            tool_context: 세션 상태를 제공하는 도구 컨텍스트.

        Returns:
            str: 만족도 평가에 활용할 요약 안내 문자열.
        """
        logger.info(f"ConfigureSatisfactionEvaluationContext called with args: {args}")

        allowed_emotions_val = args.get("allowed_emotions")
        if isinstance(allowed_emotions_val, list | tuple):
            normalized_emotions_input = [emotion for emotion in allowed_emotions_val if isinstance(emotion, str)]
        elif isinstance(allowed_emotions_val, str):
            normalized_emotions_input = [allowed_emotions_val]
        else:
            normalized_emotions_input = []
        allowed_emotions: Sequence[str] | None = normalized_emotions_input if normalized_emotions_input else None

        allowed_satisfactions_val = args.get("allowed_satisfactions")
        if isinstance(allowed_satisfactions_val, list | tuple):
            normalized_satisfactions_input = [
                satisfaction for satisfaction in allowed_satisfactions_val if isinstance(satisfaction, str)
            ]
        elif isinstance(allowed_satisfactions_val, str):
            normalized_satisfactions_input = [allowed_satisfactions_val]
        else:
            normalized_satisfactions_input = []
        allowed_satisfactions: Sequence[str] | None = (
            normalized_satisfactions_input if normalized_satisfactions_input else None
        )

        evaluation_aspect_val = args.get("evaluation_aspect")
        evaluation_aspect: str | None = evaluation_aspect_val if isinstance(evaluation_aspect_val, str) else None

        raw_text = args.get("text") or args.get("conversation_text") or args.get("conversation_text_from_file")
        text: str | None = raw_text if isinstance(raw_text, str) else None

        stored_conversation = cast(str | None, tool_context.state.get("user:conversation_text"))
        if stored_conversation and not text:
            text = stored_conversation

        conversation_preview_arg = args.get("conversation_preview")
        conversation_preview_state = tool_context.state.get("user:conversation_preview")
        conversation_preview: str | None
        if isinstance(conversation_preview_arg, str):
            conversation_preview = conversation_preview_arg
        elif isinstance(conversation_preview_state, str):
            conversation_preview = conversation_preview_state
        else:
            conversation_preview = None

        normalized_emotions = [emotion for emotion in allowed_emotions or [] if isinstance(emotion, str)]
        tool_context.actions.state_delta.update({"user:allowed_emotions": normalized_emotions})
        tool_context.state["user:allowed_emotions"] = normalized_emotions

        normalized_satisfactions = [
            satisfaction for satisfaction in allowed_satisfactions or [] if isinstance(satisfaction, str)
        ]
        tool_context.actions.state_delta.update({"user:allowed_satisfactions": normalized_satisfactions})
        tool_context.state["user:allowed_satisfactions"] = normalized_satisfactions

        if evaluation_aspect:
            tool_context.actions.state_delta.update({"user:evaluation_aspect": evaluation_aspect})
            tool_context.state["user:evaluation_aspect"] = evaluation_aspect

        headline = (
            "허용 감정 라벨: " + ", ".join(normalized_emotions) if normalized_emotions else "허용 감정 라벨 제약 없음"
        )
        satisfaction_headline = (
            "허용 만족도 라벨: " + ", ".join(normalized_satisfactions)
            if normalized_satisfactions
            else "허용 만족도 라벨 제약 없음"
        )
        aspect_headline = f"평가 측면: {evaluation_aspect}" if evaluation_aspect else "평가 측면 미지정"
        text_block = text or conversation_preview or "분석할 텍스트는 호출 시 함께 전달됩니다."

        return (
            "=== 만족도 평가 컨텍스트 ===\n"
            f"{satisfaction_headline}\n"
            f"{headline}\n"
            f"{aspect_headline}\n"
            f"분석 대상 안내: {text_block[:200]}\n"
            "============================"
        )


# 에이전트 생성부 등록
SATISFACTION_EVALUATION_AGENT = LlmAgent(
    name="satisfaction_evaluation_agent",
    model=LLM_MODEL,
    instruction=SATISFACTION_EVALUATION_PROMPT,
    tools=[ConfigureSatisfactionEvaluationContext()],
)


__all__ = [
    "ConfigureSatisfactionEvaluationContextArgs",
    "ConfigureSatisfactionEvaluationContext",
    "SATISFACTION_EVALUATION_AGENT",
]
