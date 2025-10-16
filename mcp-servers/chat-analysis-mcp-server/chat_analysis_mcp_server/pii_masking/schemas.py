"""PII 마스킹 MCP 서버용 스키마 정의 모듈"""

from __future__ import annotations

from pydantic import BaseModel, Field


class MaskPiiRequest(BaseModel):
    """PII 마스킹 요청 모델"""

    text: str = Field(..., description="마스킹할 원본 텍스트")
    mask_email: bool = Field(
        default=True,
        description="이메일을 마스킹할지 여부",
    )
    mask_phone: bool = Field(
        default=True,
        description="전화번호를 마스킹할지 여부",
    )


class MaskPiiResponse(BaseModel):
    """PII 마스킹 응답 모델"""

    masked_text: str = Field(..., description="마스킹이 적용된 텍스트")
    original_length: int = Field(..., description="원본 텍스트 길이")
    masked_length: int = Field(..., description="마스킹된 텍스트 길이")
