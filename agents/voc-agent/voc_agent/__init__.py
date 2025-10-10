"""VOC agent package."""

from core_common.logging import configure_logging, get_logger

from .telemetry.langfuse import configure_langfuse_with_settings

# Configure Langfuse tracing before importing agents so callbacks are registered once.
configure_langfuse_with_settings()

from .orchestrator.orchestration_agent import orchestrator_agent  # noqa: E402

root_agent = orchestrator_agent

__all__ = ["configure_logging", "get_logger"]
