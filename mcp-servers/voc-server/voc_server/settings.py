"""pydantic 설정 및 공용 로깅 구성 파일"""

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
    azure_openai_transcribe_deployment: str = Field(default="", min_length=1)
    azure_openai_api_version: str = Field(default="2024-12-01-preview")

    # Database 설정
    database_url: str = Field(default="sqlite:///./voc_server.db", min_length=1)
    database_echo: bool = Field(default=False)


# 설정 인스턴스 생성
settings = Settings()
