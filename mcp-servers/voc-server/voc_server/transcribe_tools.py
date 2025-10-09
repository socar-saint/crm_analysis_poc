"""Transcribe tools."""

import os
from typing import Any

from openai import AzureOpenAI

from .settings import settings

client = AzureOpenAI(
    api_key=settings.azure_openai_api_key,
    azure_endpoint=settings.azure_openai_endpoint,
    api_version=settings.azure_openai_api_version,
)


def azure_gpt_transcribe(file_path: str, language: str = "ko", timestamps: bool = False) -> Any:
    """
    ADK 자동 함수호출 호환
    - AzureOpenAI 클라이언트 사용 (api_version 명시)
    - gpt-4o-transcribe 계열은 response_format='json' (verbose_json 미지원)
    - Whisper 계열만 verbose_json 허용
    """
    try:
        if not os.path.exists(file_path):
            return {"status": "error", "error": f"file not found: {file_path}"}

        with open(file_path, "rb") as f:
            resp = client.audio.transcriptions.create(
                model=settings.azure_openai_transcribe_deployment,
                file=f,
                language=language,
                response_format="json",
                timestamp_granularities=["segment"],
            )

        if hasattr(resp, "text"):
            text = resp.text or ""
            segments = getattr(resp, "segments", None) or []
        elif isinstance(resp, dict):
            text = resp.get("text", "") or ""
            segments = resp.get("segments") or []
        else:
            text, segments = "", []

        return {"status": "ok", "text": text, "segments": segments}

    except Exception as e:
        return {"status": "error", "error": str(e)}
