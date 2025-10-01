"""pydantic 설정 및 공용 로깅 구성 파일"""

import os
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

ENV_FILES = [
    Path(__file__).resolve().parent.parent / ".env",
    Path(".env"),
]


class Settings(BaseSettings):
    """애플리케이션 설정 클래스.

    .env 파일에서 환경 변수를 로드합니다.
    """

    model_config = SettingsConfigDict(
        env_file=ENV_FILES,
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Azure OpenAI API 설정
    azure_openai_api_key: str = Field(default="", min_length=1)
    azure_openai_endpoint: str = Field(default="", min_length=1)
    azure_openai_deployment: str = Field(default="", min_length=1)
    azure_openai_api_version: str = Field(default="2024-12-01-preview")

    orchestrator_host: str = Field(
        default="0.0.0.0",  # nosec
    )
    orchestrator_port: int = Field(default=10000)
    diarization_host: str = Field(
        default="0.0.0.0",  # nosec
    )
    diarization_port: int = Field(default=10001)
    stt_mcp_sse_url: str = Field(default="http://localhost:9000/sse")

    @property
    def orchestrator_base_url(self) -> str:
        """오케스트레이션 서버 URL"""
        return f"http://{self.orchestrator_host}:{self.orchestrator_port}"

    @property
    def diarization_base_url(self) -> str:
        """다이얼라이제이션 서버 URL"""
        return f"http://{self.diarization_host}:{self.diarization_port}"


# 설정 인스턴스 생성
settings = Settings()

# for litellm
os.environ["AZURE_API_KEY"] = settings.azure_openai_api_key
os.environ["AZURE_API_BASE"] = settings.azure_openai_endpoint
os.environ["AZURE_API_VERSION"] = settings.azure_openai_api_version
