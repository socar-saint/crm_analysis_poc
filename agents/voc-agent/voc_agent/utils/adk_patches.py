"""Utilities to neutralize noisy experimental warnings in the google-adk A2A stack."""

from __future__ import annotations

import logging
from collections.abc import Iterable

logger = logging.getLogger(__name__)


def _unwrap_callable(container: object, attr: str) -> bool:
    """Replace a decorated callable with its original implementation if possible."""
    member = getattr(container, attr, None)
    unwrapped = getattr(member, "__wrapped__", None)
    if unwrapped is None:
        return False
    setattr(container, attr, unwrapped)
    return True


def _unwrap_class_init(cls: type) -> bool:
    """Restore a class __init__ that has been wrapped by an experimental decorator."""
    init_fn = getattr(cls, "__init__", None)
    if init_fn is None:
        return False
    unwrapped = getattr(init_fn, "__wrapped__", None)
    if unwrapped is None:
        return False
    cls.__init__ = unwrapped
    return True


def _unwrap_callables(container: object, attributes: Iterable[str], prefix: str) -> list[str]:
    """Unwrap simple callables on a module/object and return their identifiers."""
    patched: list[str] = []
    for attr in attributes:
        if _unwrap_callable(container, attr):
            patched.append(f"{prefix}{attr}")
    return patched


def _unwrap_class_inits(entries: Iterable[tuple[object | None, str]]) -> list[str]:
    """Unwrap __init__ for the provided class references."""
    patched: list[str] = []
    for cls, name in entries:
        if cls is not None and _unwrap_class_init(cls):  # type: ignore
            patched.append(f"{name}.__init__")
    return patched


def suppress_a2a_experimental_warnings() -> None:
    """Unwrap experimental decorators in the google-adk A2A integration."""
    try:
        from google.adk.a2a.converters import event_converter, part_converter
        from google.adk.a2a.executor import a2a_agent_executor, task_result_aggregator
        from google.adk.agents import remote_a2a_agent
    except Exception as exc:  # pragma: no cover - optional dependency might be missing
        logger.debug("Skip A2A warning suppression; google-adk modules missing: %s", exc)
        return

    patched_items: list[str] = []

    patched_items.extend(
        _unwrap_callables(
            event_converter,
            (
                "convert_a2a_message_to_event",
                "convert_a2a_part_to_genai_part",
                "convert_event_to_a2a_events",
                "convert_event_to_a2a_message",
                "convert_genai_part_to_a2a_part",
            ),
            "event_converter.",
        )
    )

    patched_items.extend(
        _unwrap_callables(
            part_converter,
            ("convert_a2a_part_to_genai_part", "convert_genai_part_to_a2a_part"),
            "part_converter.",
        )
    )

    patched_items.extend(
        _unwrap_class_inits(
            (
                (getattr(a2a_agent_executor, "A2aAgentExecutorConfig", None), "A2aAgentExecutorConfig"),
                (getattr(a2a_agent_executor, "A2aAgentExecutor", None), "A2aAgentExecutor"),
                (getattr(task_result_aggregator, "TaskResultAggregator", None), "TaskResultAggregator"),
            )
        )
    )

    patched_items.extend(
        _unwrap_class_inits(
            (getattr(remote_a2a_agent, name, None), name)
            for name in ("AgentCardResolutionError", "A2AClientError", "RemoteA2aAgent")
        )
    )

    if patched_items:
        logger.debug(
            "Suppressed google-adk A2A experimental warnings for %s",
            ", ".join(patched_items),
        )


__all__ = ["suppress_a2a_experimental_warnings"]
