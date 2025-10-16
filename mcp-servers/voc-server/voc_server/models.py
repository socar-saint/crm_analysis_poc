"""Database models and Pydantic schemas."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import ClassVar

from pydantic import BaseModel, ConfigDict, field_validator
from pydantic import Field as PydanticField
from sqlalchemy import Column, DateTime, Text
from sqlmodel import Field, SQLModel


class FeedbackRecordBase(SQLModel):
    """Shared attributes for feedback records."""

    _SUMMARY_MAX_LENGTH: ClassVar[int] = 4096

    transcript_text: str = Field(
        sa_column=Column(Text, nullable=False),
        description="STT로 변환된 상담 전체 텍스트",
    )
    summary: str = Field(
        sa_column=Column(Text, nullable=False),
        description="상담 내용을 3줄로 요약한 문장",
    )
    category: str = Field(description="상담의 주요 주제 카테고리")
    anger_level: float = Field(
        ge=0.0,
        le=1.0,
        description="고객의 화남 정도 (0.0=없음, 1.0=매우 높음)",
    )

    @field_validator("summary")
    @classmethod
    def _summary_not_empty(cls, value: str) -> str:
        value = value.strip()
        if not value:
            msg = "summary must not be empty"
            raise ValueError(msg)
        if len(value) > cls._SUMMARY_MAX_LENGTH:
            msg = f"summary must be <= {cls._SUMMARY_MAX_LENGTH} characters"
            raise ValueError(msg)
        return value


class FeedbackRecord(FeedbackRecordBase, table=True):
    """Persistent representation of a feedback record."""

    __tablename__ = "feedback_records"  # type: ignore

    id: int | None = Field(default=None, primary_key=True)
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        sa_column=Column(DateTime(timezone=True), nullable=False),
        description="레코드 생성 시각 (UTC)",
    )


class FeedbackRecordRead(FeedbackRecordBase):
    """Response schema for a stored feedback record."""

    id: int
    created_at: datetime


class InsertFeedbackPayload(BaseModel):
    """Payload schema accepted by the MCP insert feedback tool."""

    model_config = ConfigDict(extra="allow", str_strip_whitespace=True)

    transcript_text: str = PydanticField(
        ...,
        min_length=1,
        description="STT로 변환된 상담 전체 텍스트 (요약이 아닌 전체 대화)",
    )
    summary: str = PydanticField(
        ...,
        min_length=1,
        description="상담 내용을 3줄로 요약한 문장",
    )
    category: str = PydanticField(
        ...,
        min_length=1,
        description="상담의 주요 주제 카테고리",
    )
    anger_level: float = PydanticField(
        ...,
        ge=0.0,
        le=1.0,
        description="고객의 화남 정도 (0.0=없음, 1.0=매우 높음)",
    )
    transcript_file: str | None = PydanticField(
        default=None,
        description="transcribe MCP 도구가 저장한 JSON 파일 경로 (선택). 제공 시 transcript_text 검증에 활용됩니다.",
    )

    @field_validator("summary")
    @classmethod
    def _summary_not_empty(cls, value: str) -> str:
        return FeedbackRecordBase._summary_not_empty(value)  # type: ignore

    @field_validator("transcript_text")
    @classmethod
    def _transcript_not_empty(cls, value: str) -> str:
        text = value.strip()
        if not text:
            msg = "transcript_text must contain the full transcript text"
            raise ValueError(msg)
        return text
