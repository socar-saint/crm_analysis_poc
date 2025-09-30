"""응답 모델 및 텍스트 추출 유틸리티."""

import json
import re
from collections.abc import Mapping, Sequence
from typing import Any

from pydantic import RootModel


class ResponseModel(RootModel[dict[str, Any]]):
    """응답 모델."""


def parse_json_codeblock(s: str) -> Any:
    """```json ...``` 또는 일반 코드블록에서 JSON만 깔끔히 추출."""
    m = re.search(r"```(?:json)?\s*(.*)```", s, re.DOTALL | re.IGNORECASE)
    payload = m.group(1) if m else s
    start = payload.find("{")
    end = payload.rfind("}")
    if start == -1 or end == -1 or end <= start:
        return None
    try:
        return json.loads(payload[start : end + 1])
    except Exception:
        return None


def format_dialog_json(payload: Mapping[str, Any]) -> str | None:
    """{"dialog": [{"speaker": .., "text": ..}, ...]} → 'speaker: text' 줄바꿈 문자열."""
    dialog = payload.get("dialog")
    if not isinstance(dialog, Sequence) or isinstance(dialog, str | bytes):
        return None

    lines = []
    for turn in dialog:
        if not isinstance(turn, Mapping):
            continue
        speaker = turn.get("speaker")
        text = turn.get("text")
        if not (isinstance(speaker, str) and isinstance(text, str)):
            continue
        speaker = speaker.strip()
        text = text.strip()
        if speaker and text:
            lines.append(f"{speaker}: {text}")

    return "\n".join(lines) or None


def _clean_text(value: Any) -> str | None:
    if isinstance(value, str):
        stripped = value.strip()
        if stripped:
            return stripped
    return None


def _extract_text_from_content_list(content: Any) -> str | None:
    if not isinstance(content, list):
        return None
    texts: list[str] = []
    for item in content:
        if not isinstance(item, Mapping) or item.get("type") != "text":
            continue
        text = _clean_text(item.get("text"))
        if text:
            texts.append(text)
    return "\n".join(texts) if texts else None


def _extract_text_from_string_payload(value: str) -> str | None:
    payload = parse_json_codeblock(value)
    if isinstance(payload, Mapping):
        formatted = format_dialog_json(payload)
        if formatted:
            return formatted
    return _clean_text(value)


def _extract_text_from_result(result: Any) -> str | None:
    if isinstance(result, Mapping):
        text = _clean_text(result.get("text"))
        if text:
            return text

        content_text = _extract_text_from_content_list(result.get("content"))
        if content_text:
            return content_text

        structured = result.get("structuredContent")
        if isinstance(structured, Mapping):
            structured_text = _clean_text(structured.get("result"))
            if structured_text:
                return structured_text

        raw_result = result.get("result")
        if isinstance(raw_result, str):
            return _extract_text_from_string_payload(raw_result)
        return None

    if isinstance(result, str):
        return _extract_text_from_string_payload(result)

    return None


def get_human_text_from_response(resp: Mapping[str, Any] | str) -> str:
    """
    다양한 응답 스키마에서 사람이 읽기 좋은 텍스트만 뽑아내기.
    우선순위: result.text → result.content[].text → result.structuredContent.result → plain text → dialog json 파싱
    """
    if isinstance(resp, Mapping):
        direct_text = _clean_text(resp.get("text"))
        if direct_text:
            return direct_text

        result_text = _extract_text_from_result(resp.get("result"))
        if result_text:
            return result_text

        content_text = _extract_text_from_content_list(resp.get("content"))
        if content_text:
            return content_text

    if isinstance(resp, str):
        string_text = _extract_text_from_string_payload(resp)
        if string_text:
            return string_text

    return ""  # 추출 실패


def extract_response_models_from_task(task: Any) -> list[ResponseModel]:
    """task.history / task.artifacts 에 있는 data.response 사전들을 모두 모으기."""
    found: list[ResponseModel] = []

    def collect(parts: list[Any] | None) -> None:
        if not parts:
            return
        for p in parts:
            root = getattr(p, "root", None)
            data = getattr(root, "data", None)
            if isinstance(data, dict) and isinstance(data.get("response"), dict):
                found.append(ResponseModel(data["response"]))

    for msg in getattr(task, "history", []) or []:
        collect(getattr(msg, "parts", None))
    for art in getattr(task, "artifacts", []) or []:
        collect(getattr(art, "parts", None))

    return found
