"""Langfuse tracing helpers."""

import inspect
import logging
import os
from collections import OrderedDict
from collections.abc import Callable
from functools import lru_cache, wraps
from typing import Any, cast
from uuid import uuid4

import litellm

from ..settings import settings
from ..utils import configure_langfuse_environment

logger = logging.getLogger(__name__)


@lru_cache(maxsize=1)
def configure_langfuse_tracing(tags: tuple[str, ...] | None = None) -> bool:
    """Configure LiteLLM callbacks to emit traces to Langfuse.

    Args:
        tags: Optional tuple of tags that should be added to every Langfuse trace.

    Returns:
        True when Langfuse tracing is enabled, False otherwise.
    """

    if not settings.langfuse_enabled:
        logger.debug("Langfuse credentials missing; skipping tracing setup.")
        return False

    try:
        import langfuse  # noqa: F401  # Just validating the dependency is available.
    except ImportError:
        logger.warning("Langfuse package not installed; run `uv sync` to install dependencies.")
        return False

    _patch_langfuse_constructor()

    configure_langfuse_environment()

    if "langfuse" not in litellm.callbacks:
        litellm.callbacks.append("langfuse")
        logger.info("Langfuse callback registered with LiteLLM.")
    else:
        logger.debug("Langfuse callback already registered.")

    if tags:
        litellm.langfuse_default_tags = list(tags)

    return True


def configure_langfuse_with_settings(extra_tags: list[str] | None = None) -> bool:
    """Convenience wrapper to configure tracing using Settings values.

    Args:
        extra_tags: Optional list of tags appended to the default ones.
    """

    tags: list[str] = extra_tags[:] if extra_tags else []
    env_tag = os.getenv("LANGFUSE_ENVIRONMENT")
    if env_tag:
        tags.append(env_tag)
    return configure_langfuse_tracing(tuple(tags) if tags else None)


@lru_cache(maxsize=1)
def _patch_langfuse_constructor() -> None:  # noqa: C901
    """Ensure Langfuse accepts newer LiteLLM kwargs such as sdk_integration."""

    try:
        from langfuse import Langfuse
        from langfuse._client.span import LangfuseSpan  # noqa: PLC0415
    except ImportError:
        return

    signature = inspect.signature(Langfuse.__init__)
    if "sdk_integration" not in signature.parameters:
        original_init = cast(Callable[..., None], Langfuse.__init__)

        @wraps(original_init)
        def patched_init(self: Any, *args: Any, **kwargs: Any) -> None:
            kwargs.pop("sdk_integration", None)
            original_init(self, *args, **kwargs)

        Langfuse.__init__ = cast(Any, patched_init)

    if getattr(Langfuse, "_litellm_compat_installed", False):
        return

    Langfuse._litellm_compat_installed = True

    trace_cache: OrderedDict[str, _CompatTrace] = OrderedDict()  # noqa: F821

    def _extract_usage_details(params: dict[str, Any]) -> dict[str, Any] | None:
        usage_details = params.get("usage_details")
        if isinstance(usage_details, dict):
            return dict(usage_details)

        usage = params.get("usage")
        if isinstance(usage, dict):
            mapped: dict[str, Any] = {}
            for src, dst in [
                ("prompt_tokens", "prompt_tokens"),
                ("completion_tokens", "completion_tokens"),
                ("total_tokens", "total"),
                ("input", "input"),
                ("output", "output"),
            ]:
                value = usage.get(src)
                if value is not None:
                    mapped[dst] = value
            if mapped:
                return mapped
        return None

    def _collect_tags(*values: Any) -> list[str] | None:
        tags: list[str] = []
        for value in values:
            if not value:
                continue
            if isinstance(value, str):
                candidates = [value]
            elif isinstance(value, list | tuple | set):
                candidates = [item for item in value if isinstance(item, str)]
            else:
                continue
            for candidate in candidates:
                if candidate not in tags:
                    tags.append(candidate)
        return tags or None

    def _merge_metadata(
        existing: dict[str, Any] | None,
        params: dict[str, Any],
    ) -> tuple[dict[str, Any], list[str] | None]:
        metadata: dict[str, Any] = dict(existing or {})

        extra_metadata = params.get("metadata")
        if isinstance(extra_metadata, dict):
            metadata.update(extra_metadata)

        user_id = params.get("user_id") or params.get("userId")
        if user_id is not None:
            metadata["user_id"] = user_id

        session_id = params.get("session_id") or params.get("sessionId")
        if session_id is not None:
            metadata["session_id"] = session_id

        release = params.get("release")
        if release is not None:
            metadata.setdefault("release", release)

        metadata_tags = metadata.pop("tags", None)

        return metadata, _collect_tags(metadata_tags)

    def _store_trace(trace_id: str, trace: "_CompatTrace") -> None:
        trace_cache[trace_id] = trace
        trace_cache.move_to_end(trace_id)
        # Keep cache bounded to avoid unbounded growth
        if len(trace_cache) > 128:
            trace_cache.popitem(last=False)

    def _get_trace(trace_id: str) -> "_CompatTrace | None":
        trace = trace_cache.get(trace_id)
        if trace:
            trace_cache.move_to_end(trace_id)
        return trace

    class _CompatGeneration:
        def __init__(self, trace_id: str, observation: Any, generation_id: str | None = None):
            self._observation = observation
            self.trace_id = trace_id
            self.id = generation_id
            self._ended = False

        def update(self, **kwargs: Any) -> "_CompatGeneration":
            usage_details = _extract_usage_details(kwargs)
            self._observation.update(
                input=kwargs.get("input"),
                output=kwargs.get("output"),
                metadata=kwargs.get("metadata"),
                version=kwargs.get("version"),
                level=kwargs.get("level"),
                status_message=kwargs.get("status_message"),
                completion_start_time=kwargs.get("completion_start_time"),
                model=kwargs.get("model"),
                model_parameters=kwargs.get("model_parameters"),
                usage_details=usage_details,
                cost_details=kwargs.get("cost_details"),
                prompt=kwargs.get("prompt"),
            )
            return self

        def end(self, *_args: Any, **kwargs: Any) -> "_CompatGeneration":
            if self._ended:
                return self

            end_time = kwargs.pop("end_time", None) or kwargs.pop("endTime", None)
            try:
                self._observation.end(end_time=end_time)
            except Exception:
                self._observation.end()
            self._ended = True
            return self

    class _CompatSpan:
        def __init__(self, trace_id: str, observation: Any):
            self._observation = observation
            self.trace_id = trace_id

        def update(self, **kwargs: Any) -> "_CompatSpan":
            self._observation.update(
                input=kwargs.get("input"),
                output=kwargs.get("output"),
                metadata=kwargs.get("metadata"),
                version=kwargs.get("version"),
                level=kwargs.get("level"),
                status_message=kwargs.get("status_message"),
            )
            return self

        def end(self, *_args: Any, **kwargs: Any) -> "_CompatSpan":
            end_time = kwargs.pop("end_time", None) or kwargs.pop("endTime", None)
            try:
                self._observation.end(end_time=end_time)
            except Exception:
                self._observation.end()
            return self

        def generation(self, **kwargs: Any) -> "_CompatGeneration":
            usage_details = _extract_usage_details(kwargs)
            observation = self._observation.start_observation(
                name=kwargs.get("name") or "litellm-generation",
                as_type="generation",
                input=kwargs.get("input"),
                output=kwargs.get("output"),
                metadata=kwargs.get("metadata"),
                version=kwargs.get("version"),
                level=kwargs.get("level"),
                status_message=kwargs.get("status_message"),
                completion_start_time=kwargs.get("completion_start_time"),
                model=kwargs.get("model"),
                model_parameters=kwargs.get("model_parameters"),
                usage_details=usage_details,
                cost_details=kwargs.get("cost_details"),
                prompt=kwargs.get("prompt"),
            )
            return _CompatGeneration(self.trace_id, observation, kwargs.get("id"))

        def span(self, **kwargs: Any) -> "_CompatSpan":
            observation = self._observation.start_observation(
                name=kwargs.get("name") or "litellm-span",
                as_type="span",
                input=kwargs.get("input"),
                output=kwargs.get("output"),
                metadata=kwargs.get("metadata"),
                version=kwargs.get("version"),
                level=kwargs.get("level"),
                status_message=kwargs.get("status_message"),
            )
            wrapper = _CompatSpan(self.trace_id, observation)
            end_time = kwargs.get("end_time") or kwargs.get("endTime")
            if end_time is not None:
                wrapper.end(end_time=end_time)
            return wrapper

    class _CompatTrace:
        def __init__(
            self,
            client: Langfuse,
            provided_id: str,
            span: LangfuseSpan,
            metadata: dict[str, Any] | None,
            tags: list[str] | None,
        ):
            self._client = client
            self._span = span
            self.trace_id = provided_id
            self._metadata: dict[str, Any] = dict(metadata or {})
            self._tags: list[str] = list(tags or [])

        def update(self, params: dict[str, Any]) -> None:
            metadata, metadata_tags = _merge_metadata(self._metadata, params)
            tags = _collect_tags(self._tags, params.get("tags"), metadata_tags)

            self._metadata = metadata
            self._tags = tags or []

            try:
                self._span.update_trace(
                    name=params.get("name"),
                    user_id=params.get("user_id") or params.get("userId"),
                    session_id=params.get("session_id") or params.get("sessionId"),
                    version=params.get("version"),
                    input=params.get("input"),
                    output=params.get("output"),
                    metadata=metadata or None,
                    tags=tags,
                )
                self._span.update(
                    name=params.get("name"),
                    input=params.get("input"),
                    output=params.get("output"),
                    metadata=metadata or None,
                    level=params.get("level"),
                    status_message=params.get("status_message"),
                    version=params.get("version"),
                )
            except Exception:
                logger.debug("Langfuse compatibility update failed", exc_info=True)

        def generation(self, **kwargs: Any) -> _CompatGeneration:
            usage_details = _extract_usage_details(kwargs)
            observation = self._span.start_observation(
                name=kwargs.get("name") or "litellm-generation",
                as_type="generation",
                input=kwargs.get("input"),
                output=kwargs.get("output"),
                metadata=kwargs.get("metadata"),
                version=kwargs.get("version"),
                level=kwargs.get("level"),
                status_message=kwargs.get("status_message"),
                completion_start_time=kwargs.get("completion_start_time"),
                model=kwargs.get("model"),
                model_parameters=kwargs.get("model_parameters"),
                usage_details=usage_details,
                cost_details=kwargs.get("cost_details"),
                prompt=kwargs.get("prompt"),
            )
            generation = _CompatGeneration(self.trace_id, observation, kwargs.get("id"))

            generation.update(**kwargs)
            end_time = kwargs.get("end_time") or kwargs.get("endTime")
            if end_time is not None or kwargs.get("auto_end", True):
                generation.end(end_time=end_time)

            return generation

        def span(self, **kwargs: Any) -> _CompatSpan:
            observation = self._span.start_observation(
                name=kwargs.get("name") or "litellm-span",
                as_type="span",
                input=kwargs.get("input"),
                output=kwargs.get("output"),
                metadata=kwargs.get("metadata"),
                version=kwargs.get("version"),
                level=kwargs.get("level"),
                status_message=kwargs.get("status_message"),
            )
            wrapper = _CompatSpan(self.trace_id, observation)
            end_time = kwargs.get("end_time") or kwargs.get("endTime")
            if end_time is not None:
                wrapper.end(end_time=end_time)
            return wrapper

        def score(self, **kwargs: Any) -> None:
            try:
                self._span.score(**kwargs)
            except Exception:
                logger.debug("Langfuse compatibility score failed", exc_info=True)

    class _NoopGeneration:
        def __init__(self, trace_id: str):
            self.trace_id = trace_id
            self.id: str | None = None

        def update(self, **_: Any) -> "_NoopGeneration":
            return self

        def end(self, *_args: Any, **kwargs: Any) -> "_NoopGeneration":
            return self

    class _NoopSpan:
        def __init__(self, trace_id: str):
            self.trace_id = trace_id

        def update(self, **_: Any) -> "_NoopSpan":
            return self

        def end(self, *_args: Any, **kwargs: Any) -> "_NoopSpan":
            return self

        def generation(self, **_: Any) -> "_NoopGeneration":
            return _NoopGeneration(self.trace_id)

        def span(self, **_: Any) -> "_NoopSpan":
            return _NoopSpan(self.trace_id)

    class _NoopTrace:
        def __init__(self, trace_id: str):
            self.trace_id = trace_id

        def update(self, *_: Any, **__: Any) -> None:  # noqa: D401
            """No-op update for disabled Langfuse."""

        def generation(self, **_: Any) -> _NoopGeneration:
            return _NoopGeneration(self.trace_id)

        def span(self, **_: Any) -> _NoopSpan:
            return _NoopSpan(self.trace_id)

        def score(self, **_: Any) -> None:  # noqa: D401
            """No-op score for disabled Langfuse."""

    def compat_trace(self: Langfuse, **params: Any) -> Any:
        provided_id = params.get("id") or params.get("trace_id")
        if not provided_id:
            provided_id = str(uuid4())

        existing_trace = _get_trace(provided_id)
        if existing_trace:
            existing_trace.update(params)
            return existing_trace

        metadata, metadata_tags = _merge_metadata(None, params)
        tags = _collect_tags(params.get("tags"), metadata_tags)

        try:
            span = self.start_span(
                name=params.get("name") or "litellm-trace",
                input=params.get("input"),
                output=params.get("output"),
                metadata=metadata or None,
                version=params.get("version"),
                level=params.get("level"),
                status_message=params.get("status_message"),
            )
        except Exception:
            logger.debug("Langfuse compatibility trace creation failed", exc_info=True)
            return _NoopTrace(provided_id)

        compat_trace_obj = _CompatTrace(
            client=self,
            provided_id=provided_id,
            span=span,
            metadata=metadata,
            tags=tags,
        )
        compat_trace_obj.update(params)
        _store_trace(provided_id, compat_trace_obj)
        return compat_trace_obj

    if not hasattr(Langfuse, "trace"):
        Langfuse.trace = cast(Any, compat_trace)
