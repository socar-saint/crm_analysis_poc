"""pydantic 설정 및 공용 로깅 구성 파일"""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """애플리케이션 설정 클래스.

    .env 파일에서 환경 변수를 로드합니다.
    """

    model_config = SettingsConfigDict(env_file=".env")

    # API 설정
    azure_openai_api_key: str = ""
    azure_openai_endpoint: str = ""
    azure_openai_deployment: str = ""


# 설정 인스턴스 생성
settings = Settings()
