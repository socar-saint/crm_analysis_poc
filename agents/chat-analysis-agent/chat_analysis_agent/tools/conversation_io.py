"""대화 데이터를 입출력하는 도구 모음."""

from __future__ import annotations

import asyncio
import csv
from pathlib import Path
from typing import Any

from google.adk.tools import BaseTool, ToolContext
from google.genai import types
from loguru import logger
from pydantic import BaseModel, Field


class LoadCsvArgs(BaseModel):
    """CSV 기반 대화 로드 도구 인자 모델"""

    csv_path: str = Field(..., description="채팅 로그가 저장된 CSV 파일 경로")


class LoadConversationFromCsvTool(BaseTool):
    """CSV 파일에서 채팅 로그를 읽어 세션 상태에 저장하는 도구"""

    REQUIRED_COLUMNS = {"conversation_id", "source", "message"}

    def __init__(self) -> None:
        """LoadConversationFromCsvTool 도구를 초기화한다."""
        super().__init__(
            name="load_conversation_from_csv",
            description="CSV 파일에서 채팅 로그 데이터를 로드한다.",
        )

    def _get_declaration(self) -> types.FunctionDeclaration:
        """도구 스키마를 FunctionDeclaration 형식으로 반환한다.

        Returns:
            types.FunctionDeclaration: 도구 선언 객체.
        """
        schema_dict = LoadCsvArgs.model_json_schema()
        schema_dict.pop("title", None)
        return types.FunctionDeclaration(
            name=self.name,
            description=self.description,
            parameters=types.Schema.model_validate(schema_dict),
        )

    def run(self, *, args: dict[str, Any], tool_context: ToolContext) -> str:
        """도구를 동기적으로 실행한다.

        Args:
            args: 도구 호출 인자.
            tool_context: 세션 상태를 제공하는 컨텍스트.

        Returns:
            str: CSV에서 결합한 전체 대화 텍스트.
        """
        return asyncio.get_event_loop().run_until_complete(self.run_async(args=args, tool_context=tool_context))

    async def run_async(
        self,
        *,
        args: dict[str, Any],
        tool_context: ToolContext,
    ) -> str:
        """CSV 파일에서 채팅 로그 데이터를 읽어 정리된 텍스트를 반환한다.

        Args:
            args: 도구 호출 시 전달된 인자 사전.
            tool_context: 세션 상태와 동작을 제공하는 도구 컨텍스트.

        Returns:
            str: 사용자와 상담원의 발화를 합친 전체 대화 텍스트.
        """
        logger.info(f"LoadConversationFromCsvTool called with args: {args}")

        csv_path_val = args.get("csv_path")
        if not isinstance(csv_path_val, str) or not csv_path_val.strip():
            raise RuntimeError("Argument csv_path is required.")

        path = Path(csv_path_val).expanduser().resolve()
        if not path.exists():
            raise RuntimeError(f"CSV file not found: {path}")

        rows = self._read_csv(path=path)
        transcript_lines = [
            f"{row['source']}: {row['message']}"
            for row in rows
            if isinstance(row.get("source"), str) and isinstance(row.get("message"), str)
        ]
        logger.info(f"Loaded {len(transcript_lines)} rows from CSV file")

        full_transcript = "\n".join(transcript_lines)

        tool_context.actions.state_delta.update(
            {
                "user:conversation_text": full_transcript,
                "user:conversation_source_path": str(path),
            }
        )
        tool_context.state["user:conversation_text"] = full_transcript
        tool_context.state["user:conversation_source_path"] = str(path)

        return full_transcript

    def _read_csv(self, path: Path) -> list[dict[str, Any]]:
        """CSV 파일을 읽어 Dictionary 형태의 목록으로 반환한다.

        Args:
            path: CSV 파일 경로.

        Returns:
            List[Dict[str, Any]]: 읽어들인 CSV 행의 목록.
        """
        with path.open("r", encoding="utf-8", newline="") as csv_file:
            reader = csv.DictReader(csv_file)
            if reader.fieldnames is None:
                raise RuntimeError("Header not found in CSV file.")
            missing_columns = self.REQUIRED_COLUMNS.difference(reader.fieldnames)
            if missing_columns:
                joined_columns = ", ".join(sorted(missing_columns))
                raise RuntimeError(f"Required columns not found in CSV file: {joined_columns}")
            return [dict(row) for row in reader]
