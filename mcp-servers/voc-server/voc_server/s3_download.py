"""S3 프리픽스를 로컬 파일 시스템으로 다운로드하는 도구."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

import boto3

__all__ = ["download_s3_prefix", "parse_s3_uri"]

logger = logging.getLogger(__name__)


def parse_s3_uri(s3_uri: str) -> tuple[str, str]:
    """s3://bucket/key 형태의 URI를 버킷과 프리픽스로 분리한다."""
    if not s3_uri.startswith("s3://"):
        raise ValueError(f"잘못된 S3 URI입니다: {s3_uri}")

    without_scheme = s3_uri[5:]
    parts = without_scheme.split("/", 1)
    bucket = parts[0]
    prefix = parts[1] if len(parts) > 1 else ""
    if prefix and not prefix.endswith("/"):
        prefix += "/"
    return bucket, prefix


def download_s3_prefix(s3_uri: str, destination_dir: str | Path | None = None) -> dict[str, Any]:
    """지정한 ``s3_uri`` 아래의 객체를 ``destination_dir``에 다운로드한다."""
    bucket, prefix = parse_s3_uri(s3_uri)

    session = boto3.Session()
    client = session.client("s3")

    if destination_dir is None:
        destination_path = Path.cwd() / "downloads"
    else:
        destination_path = Path(destination_dir)

    destination_path.mkdir(parents=True, exist_ok=True)
    logger.info("[s3_download] 다운로드 시작: uri=%s, 경로=%s", s3_uri, destination_path)

    response = client.list_objects_v2(Bucket=bucket, Prefix=prefix)
    contents = response.get("Contents", [])

    downloaded = 0
    for obj in contents:
        key = obj["Key"]
        if key.endswith("/"):
            continue
        relative_key = key[len(prefix) :] if prefix and key.startswith(prefix) else key
        local_path = destination_path / relative_key
        local_path.parent.mkdir(parents=True, exist_ok=True)
        client.download_file(bucket, key, str(local_path))
        downloaded += 1
        logger.info("[s3_download] 파일 저장: %s", local_path)

    if downloaded == 0:
        logger.warning("[s3_download] 다운로드할 객체를 찾지 못했습니다: %s", s3_uri)

    return {
        "s3_uri": s3_uri,
        "destination": str(destination_path),
        "downloaded_files": downloaded,
    }
