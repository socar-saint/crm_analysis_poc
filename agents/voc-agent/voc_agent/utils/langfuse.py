"""Utilities for configuring Langfuse usage across the VOC agent."""

import os

from ..settings import settings


def configure_langfuse_environment() -> None:
    """Ensure Langfuse-related environment variables are present."""

    if settings.langfuse_host:
        os.environ.setdefault("LANGFUSE_HOST", settings.langfuse_host)
    if settings.langfuse_public_key:
        os.environ.setdefault("LANGFUSE_PUBLIC_KEY", settings.langfuse_public_key)
    if settings.langfuse_secret_key:
        os.environ.setdefault("LANGFUSE_SECRET_KEY", settings.langfuse_secret_key)
    if settings.langfuse_release:
        os.environ.setdefault("LANGFUSE_RELEASE", settings.langfuse_release)
