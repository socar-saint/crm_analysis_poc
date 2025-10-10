"""Server."""

import json
import logging
from pathlib import Path
from typing import Any

from mcp.server.fastmcp import FastMCP

from .audiofile_tools import opus2wav
from .pi_masking import mask_pii
from .s3_download import download_s3_prefix
from .transcribe_tools import azure_gpt_transcribe
from .wav_diarization import diarize_stereo_wav

mcp = FastMCP("STT Server", host="0.0.0.0", port=9000)  # nosec


@mcp.tool(description="Masking private information contained in context")
def mask_pii_tool(text: str) -> str:
    """Masking private information contained in context."""
    logging.info("[mask_pii] len(text)=%d", len(text))
    s = mask_pii(text)
    logging.info("[mask_pii] masked_len=%d", len(s))
    return s


@mcp.tool(description="Convert .opus/.ogg to 16kHz 2ch PCM16 .wav")
def opus2wav_tool(input_path: str, out_dir: str, sr: int, ch: int) -> Any:
    """Convert .opus/.ogg to 16kHz 2ch PCM16 .wav."""
    logging.info("[opus2wav] input file: %s", input_path)
    s = opus2wav(input_path, out_dir, sr, ch)
    logging.info("[opus2wav] output file: %s", out_dir)
    logging.info("[opus2wav] result: %s", s)
    return s


@mcp.tool(description="Transcribe audio file using gpt-4o-transcribe via Azure")
def gpt_transcribe_tool(file_path: str, language: str, timestamps: bool) -> Any:
    """Transcribe audio file using gpt-4o-transcribe via Azure."""

    logging.info("[azure_gpt_transcribe] audio file: %s", file_path)
    s = azure_gpt_transcribe(file_path, language, timestamps)
    logging.info("[azure_gpt_transcribe] result: %s", s)

    if isinstance(s, dict) and s.get("status") == "ok":
        downloads_dir = Path.cwd() / "downloads" / "transcriptions"
        downloads_dir.mkdir(parents=True, exist_ok=True)

        base_name = Path(file_path).stem or "transcription"
        output_path = downloads_dir / f"{base_name}.json"
        if output_path.exists():
            counter = 1
            while True:
                candidate = downloads_dir / f"{base_name}_{counter}.json"
                if not candidate.exists():
                    output_path = candidate
                    break
                counter += 1

        try:
            with output_path.open("w", encoding="utf-8") as f:
                json.dump(s, f, ensure_ascii=False, indent=2)
        except Exception as exc:
            logging.exception("[azure_gpt_transcribe] failed to save result: %s", exc)
            s["saved_file_error"] = str(exc)
        else:
            s["saved_file"] = str(output_path)
            logging.info("[azure_gpt_transcribe] saved file: %s", output_path)

    return s


@mcp.tool(description="Diarize a two-channel PCM WAV file by per-channel energy analysis")
def diarize_wav_tool(
    file_path: str,
    frame_seconds: float | None = None,
    silence_threshold: float | None = None,
    overlap_margin: float | None = None,
    min_segment_seconds: float | None = None,
    output_dir: str | None = None,
) -> Any:
    """Expose the stereo WAV diarizer via FastMCP."""

    logging.info("[diarize_wav] file=%s", file_path)

    def _as_float(value: Any) -> float | None:
        if value is None:
            return None
        try:
            return float(value)
        except (TypeError, ValueError):
            return None

    result = diarize_stereo_wav(
        file_path=file_path,
        frame_seconds=_as_float(frame_seconds),
        silence_threshold=_as_float(silence_threshold),
        overlap_margin=_as_float(overlap_margin),
        min_segment_seconds=_as_float(min_segment_seconds),
        output_dir=output_dir,
    )
    logging.info(
        "[diarize_wav] status=%s segments=%d",
        result.get("status"),
        len(result.get("segments", [])) if isinstance(result, dict) else -1,
    )
    return result


@mcp.tool(description="S3 uri로 된 파일을 로컬에 다운로드하고, 다운로드한 파일의 경로를 반환합니다.")
def s3_download_tool(s3_uri: str) -> dict[str, Any]:
    """주어진 ``s3_uri`` 아래 객체를 임시 디렉터리에 다운로드한다."""
    result = download_s3_prefix(s3_uri)
    logging.info("[s3_download] 결과=%s", result)
    return result


# Main entry point with graceful shutdown handling
if __name__ == "__main__":
    mcp.run(transport="sse")
