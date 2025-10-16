"""PII 마스킹 로직을 제공하는 모듈"""

import re

from loguru import logger

EMAIL_PATTERN = re.compile(r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}")
PHONE_PATTERN = re.compile(r"(?:\+?\d{1,3}[-\s]?)?(?:\d{2,4}[-\s]?){2,3}\d{3,4}")


def mask_text(
    *,
    text: str,
    mask_email: bool = True,
    mask_phone: bool = True,
) -> str:
    """텍스트에서 이메일과 전화번호를 마스킹한다.

    Args:
        text: 마스킹할 원본 문자열.
        mask_email: 이메일을 마스킹할지 여부.
        mask_phone: 전화번호를 마스킹할지 여부.

    Returns:
        str: 개인정보가 마스킹된 문자열.
    """
    logger.info(f"Masking text: {text}, mask_email: {mask_email}, mask_phone: {mask_phone}")

    masked = text
    if mask_email:
        masked = EMAIL_PATTERN.sub("<EMAIL>", masked)
    if mask_phone:
        masked = PHONE_PATTERN.sub("<PHONE>", masked)

    return masked
