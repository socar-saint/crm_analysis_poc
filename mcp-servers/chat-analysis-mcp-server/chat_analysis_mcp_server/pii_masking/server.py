"""fastmcp 기반 PII 마스킹 MCP 서버 진입점"""

from __future__ import annotations

import os

from fastmcp import FastMCP
from starlette.requests import Request
from starlette.responses import JSONResponse

from .masking import mask_text
from .schemas import (
    MaskPiiRequest,
    MaskPiiResponse,
)

app = FastMCP(
    name="PII Masking MCP Server",
    instructions="이메일과 전화번호를 마스킹하는 MCP 서버",
    version="0.1.0",
)


@app.tool(
    name="mask_conversation_pii",
    description="텍스트에서 이메일과 전화번호를 마스킹한다.",
)
async def mask_conversation_pii(
    text: str,
    mask_email: bool = True,
    mask_phone: bool = True,
) -> MaskPiiResponse:
    """PII 마스킹 도구 엔드포인트."""
    request = MaskPiiRequest(text=text, mask_email=mask_email, mask_phone=mask_phone)
    masked = mask_text(
        text=request.text,
        mask_email=request.mask_email,
        mask_phone=request.mask_phone,
    )
    return MaskPiiResponse(
        masked_text=masked,
        original_length=len(request.text),
        masked_length=len(masked),
    )


@app.custom_route("/mask", ["POST"])
async def http_mask(request: Request) -> JSONResponse:
    """HTTP 호출로도 마스킹 기능을 제공한다."""
    payload = await request.json()
    mask_request = MaskPiiRequest.model_validate(payload)
    response = await mask_conversation_pii(
        text=mask_request.text,
        mask_email=mask_request.mask_email,
        mask_phone=mask_request.mask_phone,
    )
    return JSONResponse(response.model_dump())


def run() -> None:
    """서버를 실행한다."""
    host = os.getenv("PII_MASKING_SERVER_HOST", "0.0.0.0")  # nosec
    port = int(os.getenv("PII_MASKING_SERVER_PORT", "50000"))  # nosec
    sse_path = os.getenv("PII_MASKING_SERVER_SSE_PATH", "/sse")
    app.run(transport="sse", host=host, port=port, path=sse_path)


if __name__ == "__main__":
    run()
