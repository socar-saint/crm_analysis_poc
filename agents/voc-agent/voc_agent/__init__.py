"""VOC agent package."""

from core_common.logging import configure_logging, get_logger

from .orchestrator.orchestration_agent import orchestrator_agent

root_agent = orchestrator_agent

__all__ = ["configure_logging", "get_logger"]
