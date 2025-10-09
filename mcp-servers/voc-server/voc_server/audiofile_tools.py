"""Audio file tools."""

import os
import subprocess
from typing import Any


def opus2wav(input_path: str, out_dir: str, sr: int, ch: int) -> Any:
    """
    Opus 포맷 녹음파일을 LLM transcribe가 읽을 수 있는 wav 포맷으로 변환한다.
    ADK 자동 함수호출 호환: 파라미터 기본값 금지
       - out_dir, sr, ch 모두 필수 인자
       - 호출자가 빈 문자열/0을 넣어도 여기서 기본값 보정

    Returns:
      {"status":"ok","wav_path": "..."} or {"status":"error","error": "..."}
    """

    if not os.path.exists(input_path):
        return {"status": "error", "error": f"file not found: {input_path}"}

    # 기본값 보정 (필수 인자지만, LLM이 빈 값을 넣을 수 있으므로 내부에서 방어)
    if not out_dir:
        out_dir = os.path.join(os.path.dirname(input_path), "wav_out")
    if sr <= 0:
        sr = 16000
    if ch <= 0:
        ch = 2

    os.makedirs(out_dir, exist_ok=True)
    base = os.path.splitext(os.path.basename(input_path))[0]
    out_path = os.path.abspath(os.path.join(out_dir, base + ".wav"))

    ffmpeg_bin = _resolve_ffmpeg()
    if not ffmpeg_bin:
        return {
            "status": "error",
            "error": "ffmpeg binary not found in PATH and imageio-ffmpeg unavailable",
        }

    cmd = [
        ffmpeg_bin,
        "-y",
        "-i",
        input_path,
        "-ac",
        str(ch),
        "-ar",
        str(sr),
        "-acodec",
        "pcm_s16le",
        out_path,
    ]

    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, check=False)
    except Exception as e:  # subprocess may raise e.g. FileNotFoundError
        return {"status": "error", "error": str(e)}

    if proc.returncode != 0:
        return {"status": "error", "error": proc.stderr or proc.stdout}

    result = {"status": "ok", "wav_path": out_path}
    return result


def _resolve_ffmpeg() -> str | None:
    """Locate an ffmpeg executable, falling back to imageio-ffmpeg when possible."""
    from shutil import which

    binary = which("ffmpeg")
    if binary:
        return binary

    try:
        import imageio_ffmpeg

        return imageio_ffmpeg.get_ffmpeg_exe()  # type: ignore
    except Exception:
        return None
