"""Transcribe tools."""

import os
from typing import Any

from dotenv import load_dotenv
from openai import AzureOpenAI

load_dotenv()


def azure_gpt_transcribe(file_path: str, language: str, timestamps: bool) -> Any:
    """
    ADK 자동 함수호출 호환: 파라미터 기본값 없음
    - AzureOpenAI 클라이언트 사용 (api_version 명시)
    - gpt-4o-transcribe 계열은 response_format='json' (verbose_json 미지원)
    - Whisper 계열만 verbose_json 허용
    """
    try:
        if not os.path.exists(file_path):
            return {"status": "error", "error": f"file not found: {file_path}"}

        api_key = os.getenv("AZURE_OPENAI_API_KEY")
        endpoint = os.getenv("AZURE_OPENAI_ENDPOINT")
        api_version = (
            os.getenv("AZURE_OPENAI_API_VERSION") or
            os.getenv("OPENAI_API_VERSION") or
            "2023-12-01-preview"
        )
        if not api_key or not endpoint:
            return {"status": "error", "error": "missing AZURE_OPENAI_API_KEY or AZURE_OPENAI_ENDPOINT"}

        client = AzureOpenAI(
            api_key=api_key,
            azure_endpoint=endpoint,
            api_version=api_version,
        )

        # --- 배포 이름(Deployment name) 사용
        deploy = os.getenv("AZURE_OPENAI_TRANSCRIBE_DEPLOYMENT", "").strip()
        if not deploy:
            deploy = "gpt-4o-transcribe"

        if language:
            lang = language.strip().lower().replace("_", "-").split("-")[0]
        else:
            lang = "ko"
        ts = bool(timestamps)

        # --- 모델에 따른 response_format 강제
        # gpt-4o-transcribe 계열은 verbose_json 미지원 → json or text
        if "gpt-4o-transcribe" in deploy or deploy.startswith("gpt-4o"):
            response_format = "json"
        else:
            # Whisper 등에서는 verbose_json로 segment 포함 응답 가능
            response_format = "verbose_json" if ts else "json"

        with open(file_path, "rb") as f:
            resp = client.audio.transcriptions.create(
                model=deploy,
                file=f,
                language=lang,
                response_format=response_format,
            )

        os.remove(file_path)

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
