"""pydantic 설정 및 공용 로깅 구성 파일"""

import os
from pathlib import Path

from pydantic import AliasChoices, Field
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

    # 서버 바인딩 주소 (0.0.0.0 = 모든 인터페이스에서 수신)
    orchestrator_host: str = Field(default="0.0.0.0")  # nosec
    orchestrator_port: int = Field(default=10000)
    audio_processing_host: str = Field(
        default="0.0.0.0",  # nosec
        validation_alias=AliasChoices("AUDIO_PROCESSING_HOST", "DIARIZATION_HOST"),
    )
    audio_processing_port: int = Field(
        default=10001,
        validation_alias=AliasChoices("AUDIO_PROCESSING_PORT", "DIARIZATION_PORT"),
    )

    # Agent card에 노출될 공개 URL용 호스트 이름
    orchestrator_public_host: str = Field(default="localhost")
    audio_processing_public_host: str = Field(
        default="localhost",
        validation_alias=AliasChoices(
            "AUDIO_PROCESSING_PUBLIC_HOST",
            "DIARIZATION_PUBLIC_HOST",
        ),
    )
    consultation_analysis_host: str = Field(
        default="0.0.0.0",  # nosec
        validation_alias="CONSULTATION_ANALYSIS_HOST",
    )
    consultation_analysis_port: int = Field(
        default=10002,
        validation_alias="CONSULTATION_ANALYSIS_PORT",
    )
    consultation_analysis_public_host: str = Field(
        default="localhost",
        validation_alias="CONSULTATION_ANALYSIS_PUBLIC_HOST",
    )

    stt_mcp_sse_url: str = Field(default="http://localhost:9000/sse")

    @property
    def orchestrator_base_url(self) -> str:
        """오케스트레이션 서버 URL (클라이언트 연결용)"""
        return f"http://{self.orchestrator_public_host}:{self.orchestrator_port}"

    @property
    def audio_processing_base_url(self) -> str:
        """오디오 처리 서버 URL (클라이언트 연결용)"""
        return f"http://{self.audio_processing_public_host}:{self.audio_processing_port}"

    @property
    def consultation_analysis_base_url(self) -> str:
        """상담 분석 서버 URL (클라이언트 연결용)"""
        return f"http://{self.consultation_analysis_public_host}:{self.consultation_analysis_port}"

    # Backward compatibility helpers (deprecated diarization terminology)
    @property
    def diarization_host(self) -> str:
        """다이얼라이제이션 서버 호스트 (호환용)"""
        return self.audio_processing_host

    @property
    def diarization_port(self) -> int:
        """다이얼라이제이션 서버 포트 (호환용)"""
        return self.audio_processing_port

    @property
    def diarization_public_host(self) -> str:
        """다이얼라이제이션 서버 퍼블릭 호스트 (호환용)"""
        return self.audio_processing_public_host

    @property
    def diarization_base_url(self) -> str:
        """다이얼라이제이션 서버 URL (호환용)"""
        return self.audio_processing_base_url


# 설정 인스턴스 생성
settings = Settings()

# for litellm
os.environ["AZURE_API_KEY"] = settings.azure_openai_api_key
os.environ["AZURE_API_BASE"] = settings.azure_openai_endpoint
os.environ["AZURE_API_VERSION"] = settings.azure_openai_api_version
