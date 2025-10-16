"""pydantic 설정 및 공용 로깅 구성 파일"""

import logging
import os
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """애플리케이션 설정 클래스.

    .env 파일에서 환경 변수를 로드합니다.
    """

    model_config = SettingsConfigDict(env_file=".env")

    # OpenAI API 설정
    OPENAI_API_KEY: str = ""
    OPENAI_MODEL: str = "gpt-4"
    
    # Azure OpenAI 설정
    AZURE_OPENAI_API_KEY: str = ""
    AZURE_OPENAI_ENDPOINT: str = ""
    AZURE_OPENAI_API_VERSION: str = "2024-02-15-preview"
    AZURE_OPENAI_DEPLOYMENT_NAME: str = "gpt-4"
    
    # Google API 설정
    GOOGLE_API_KEY: str = ""


# 설정 인스턴스 생성
settings = Settings()


# ==== Azure LLM 싱글톤 인스턴스 ====

# Azure OpenAI LLM 인스턴스 (전역으로 한 번만 생성)
_azure_llm = None

def get_azure_llm():
    """Azure LLM 싱글톤 인스턴스를 반환합니다."""
    global _azure_llm
    if _azure_llm is None:
        from google.adk.models.lite_llm import LiteLlm
        _azure_llm = LiteLlm(
            model=f"azure/{settings.AZURE_OPENAI_DEPLOYMENT_NAME}",
            api_key=settings.AZURE_OPENAI_API_KEY,
            api_base=settings.AZURE_OPENAI_ENDPOINT,
            api_version=settings.AZURE_OPENAI_API_VERSION,
        )
    return _azure_llm

# 편의를 위한 전역 변수
azure_llm = get_azure_llm()


# ==== 공용 로깅 설정 ====


def _configure_logging_once() -> None:
    """루트 로거를 한 번만 구성합니다.

    환경 변수:
    - LOG_LEVEL: 기본 INFO
    - LOG_FORMAT: 기본 "%(asctime)s %(levelname)s %(name)s: %(message)s"
    - LOG_DATE_FORMAT: 기본 "%Y-%m-%d %H:%M:%S"
    - LOG_FILE: 설정 시 로테이팅 파일 핸들러 추가
    - LOG_MAX_BYTES: 파일 최대 크기(기본 10MB)
    - LOG_BACKUP_COUNT: 보관 파일 개수(기본 5)
    """
    if getattr(_configure_logging_once, "_configured", False):
        return

    level_name = os.getenv("LOG_LEVEL", "INFO").upper()
    level = getattr(logging, level_name, logging.INFO)

    root_logger = logging.getLogger()
    root_logger.setLevel(level)

    # 기존 핸들러가 없다면 기본 핸들러 구성
    if not root_logger.handlers:
        log_format = os.getenv("LOG_FORMAT", "%(asctime)s %(levelname)s %(name)s: %(message)s")
        date_format = os.getenv("LOG_DATE_FORMAT", "%Y-%m-%d %H:%M:%S")
        formatter = logging.Formatter(fmt=log_format, datefmt=date_format)

        stream_handler = logging.StreamHandler()
        stream_handler.setLevel(level)
        stream_handler.setFormatter(formatter)
        root_logger.addHandler(stream_handler)

        log_file = os.getenv("LOG_FILE")
        if log_file:
            try:
                from logging.handlers import (
                    RotatingFileHandler,
                )  # pylint: disable=import-outside-toplevel

                log_path = Path(log_file)
                if log_path.parent:
                    log_path.parent.mkdir(parents=True, exist_ok=True)

                max_bytes = int(os.getenv("LOG_MAX_BYTES", str(10_000_000)))
                backup_count = int(os.getenv("LOG_BACKUP_COUNT", "5"))

                file_handler = RotatingFileHandler(log_path, maxBytes=max_bytes, backupCount=backup_count)
                file_handler.setLevel(level)
                file_handler.setFormatter(formatter)
                root_logger.addHandler(file_handler)
            except Exception:  # 파일 핸들러 구성 실패 시 스트림 로깅만 사용
                root_logger.exception("Failed to configure file logging; fallback to stdout only.")

    setattr(_configure_logging_once, "_configured", True)


def get_logger(name: str | None = None) -> logging.Logger:
    """공용 로거 헬퍼. 설정을 보장하고 요청한 이름의 로거를 반환합니다."""
    _configure_logging_once()
    return logging.getLogger(name) if name else logging.getLogger(__name__)

