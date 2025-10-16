"""개인정보(PII) 마스킹 도구 모듈"""

from __future__ import annotations

import asyncio
import os
from typing import Any

from fastmcp.client import Client, SSETransport
from google.adk.tools import BaseTool, ToolContext
from google.genai import types
from loguru import logger
from pydantic import BaseModel, Field

PII_MASKING_SERVER_URL = os.getenv("PII_MASKING_SERVER_URL", "http://localhost:50000")


class MaskPiiArgs(BaseModel):
    """PII 마스킹 도구 인자 모델"""

    text: str = Field(..., description="마스킹할 원본 텍스트")
    mask_email: bool = Field(
        default=True,
        description="이메일을 마스킹할지 여부",
    )
    mask_phone: bool = Field(
        default=True,
        description="전화번호를 마스킹할지 여부",
    )


class MaskPiiTool(BaseTool):
    """개인정보 마스킹 도구"""

    def __init__(self) -> None:
        """MaskPiiTool 도구를 초기화한다."""
        super().__init__(
            name="mask_conversation_pii",
            description="대화 텍스트에서 이메일과 전화번호 등을 마스킹한다.",
        )
        self._service_url = f"{PII_MASKING_SERVER_URL}/sse"

    def _get_declaration(self) -> types.FunctionDeclaration:
        """도구 스키마를 FunctionDeclaration 형식으로 반환한다.

        Returns:
            types.FunctionDeclaration: 도구 선언 객체.
        """
        schema_dict = MaskPiiArgs.model_json_schema()
        schema_dict.pop("title", None)
        return types.FunctionDeclaration(
            name=self.name,
            description=self.description,
            parameters=types.Schema.model_validate(schema_dict),
        )

    def run(self, *, args: dict[str, Any], tool_context: ToolContext) -> str:
        """도구를 동기적으로 실행한다."""
        loop = asyncio.get_event_loop()
        return loop.run_until_complete(self.run_async(args=args, tool_context=tool_context))

    async def run_async(
        self,
        *,
        args: dict[str, Any],
        tool_context: ToolContext,
    ) -> str:
        """PII를 마스킹한 텍스트를 반환하고 상태에 저장한다."""
        logger.info(f"MaskPiiTool called with args: {args}")
        parsed_args = MaskPiiArgs(**args)

        masked_text = await self._mask_via_mcp(parsed_args)

        tool_context.actions.state_delta.update(
            {
                "user:conversation_text": masked_text,
                "user:conversation_text_masked": masked_text,
            }
        )
        tool_context.state["user:conversation_text"] = masked_text
        tool_context.state["user:conversation_text_masked"] = masked_text

        return masked_text

    async def _mask_via_mcp(self, args: MaskPiiArgs) -> str:
        """MCP 서버를 호출해 마스킹을 수행한다."""
        if not self._service_url:
            raise RuntimeError("PII masking server URL is not set.")

        transport = SSETransport(url=self._service_url)
        client = Client(transport)

        try:
            async with client:
                result = await client.call_tool(
                    name="mask_conversation_pii",
                    arguments=args.model_dump(),
                )
        except Exception as exc:  # noqa: BLE001
            logger.warning(f"MCP server call failed: {exc}")
            raise RuntimeError("PII masking MCP server call failed.") from exc

        if result.is_error:
            raise RuntimeError("PII masking MCP server returned an error.")

        structured = result.structured_content
        if isinstance(structured, dict):
            masked_text = structured.get("masked_text")
            if isinstance(masked_text, str):
                return masked_text

        for block in result.content:
            text = getattr(block, "text", None)
            if isinstance(text, str) and text:
                return text

        raise RuntimeError("PII masking MCP server response did not contain masking result.")


__all__ = [
    "MaskPiiArgs",
    "MaskPiiTool",
]
