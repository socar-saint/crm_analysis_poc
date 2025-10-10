"""UI for simple test settings"""

import re
from pathlib import Path
from typing import Annotated, Any

from pydantic import AliasChoices, Field
from pydantic_settings import BaseSettings, SettingsConfigDict

ENV_FILES = [
    Path(__file__).resolve().parent.parent / ".env",
    Path(".env"),
]


def _parse_recommended_questions(value: Any) -> list[str]:
    """환경 변수로 전달된 추천 질문 문자열을 리스트로 변환."""
    if value is None or value == "":
        return []
    if isinstance(value, list):
        return [str(item).strip() for item in value if str(item).strip()]
    if isinstance(value, str):
        parts = re.split(r"[\n,|]", value)
        return [part.strip() for part in parts if part and part.strip()]
    return []


class Settings(BaseSettings):
    """UI 애플리케이션 설정 클래스."""

    model_config = SettingsConfigDict(
        env_file=ENV_FILES,
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # 오케스트레이터 연결 설정
    orchestrator_host: str = Field(default="localhost")
    orchestrator_port: int = Field(default=10000)
    recommended_questions_input: Annotated[
        str | None,
        Field(
            default=None,
            alias="RECOMMENDED_QUESTIONS",
            validation_alias=AliasChoices("RECOMMENDED_QUESTIONS", "recommended_questions"),
        ),
    ] = None

    @property
    def recommended_questions(self) -> list[str]:
        """추천 질문 목록."""
        return _parse_recommended_questions(self.recommended_questions_input)

    @property
    def orchestrator_base_url(self) -> str:
        """오케스트레이션 서버 URL"""
        return f"http://{self.orchestrator_host}:{self.orchestrator_port}"


# 설정 인스턴스 생성
settings = Settings()
