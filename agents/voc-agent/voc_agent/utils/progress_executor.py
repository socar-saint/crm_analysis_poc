"""Extended A2A executor that emits richer progress status updates."""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Awaitable, Callable, Iterable
from datetime import UTC, datetime
from typing import Any
from uuid import uuid4

from a2a.server.agent_execution import RequestContext
from a2a.server.events import EventQueue
from a2a.types import (
    Artifact,
    Message,
    Role,
    TaskArtifactUpdateEvent,
    TaskState,
    TaskStatus,
    TaskStatusUpdateEvent,
    TextPart,
)
from google.adk.a2a.executor.a2a_agent_executor import (
    A2aAgentExecutor,
    A2aAgentExecutorConfig,
    convert_a2a_request_to_adk_run_args,
    convert_event_to_a2a_events,
)
from google.adk.a2a.executor.task_result_aggregator import TaskResultAggregator
from google.adk.events.event import Event
from google.adk.runners import InvocationContext, Runner
from google.adk.utils.context_utils import Aclosing

ProgressKey = tuple[str, str | None]


class ProgressAwareA2aAgentExecutor(A2aAgentExecutor):
    """Adds human-readable progress TaskStatus updates during execution."""

    _DEFAULT_PROGRESS_LABELS: dict[ProgressKey, str | None] = {
        ("start", None): None,
        ("finalizing", None): "최종 응답을 구성하고 있습니다...",
    }

    def __init__(
        self,
        *,
        runner: Runner | Callable[..., Runner | Awaitable[Runner]],
        config: A2aAgentExecutorConfig | None = None,
        progress_labels: dict[ProgressKey, str | None] | None = None,
    ) -> None:
        """init"""
        super().__init__(runner=runner, config=config)
        self._progress_labels: dict[ProgressKey, str | None] = {
            **self._DEFAULT_PROGRESS_LABELS,
            **(progress_labels or {}),
        }
        self._emitted_progress: dict[str, set[ProgressKey]] = defaultdict(set)

    async def _handle_request(
        self,
        context: RequestContext,
        event_queue: EventQueue,
    ) -> None:
        task_id = context.task_id or ""
        self._emitted_progress.pop(task_id, None)

        runner = await self._resolve_runner()

        run_args = convert_a2a_request_to_adk_run_args(context, self._config.a2a_part_converter)

        session = await self._prepare_session(context, run_args, runner)

        invocation_context = runner._new_invocation_context(
            session=session,
            new_message=run_args["new_message"],
            run_config=run_args["run_config"],
        )

        initial_event = TaskStatusUpdateEvent(
            task_id=context.task_id,
            status=TaskStatus(
                state=TaskState.working,
                timestamp=datetime.now(UTC).isoformat(),
                message=self._build_message(self._label_for(("start", None))),
            ),
            context_id=context.context_id,
            final=False,
            metadata={
                _get_adk_metadata_key("app_name"): runner.app_name,
                _get_adk_metadata_key("user_id"): run_args["user_id"],
                _get_adk_metadata_key("session_id"): run_args["session_id"],
            },
        )
        await event_queue.enqueue_event(initial_event)

        task_result_aggregator = TaskResultAggregator()
        task_result_aggregator.process_event(initial_event)

        try:
            async with Aclosing(runner.run_async(**run_args)) as agen:
                async for adk_event in agen:
                    progress_events = self._progress_events_from_adk_event(adk_event, context, invocation_context)
                    await self._enqueue_events(event_queue, task_result_aggregator, progress_events)

                    converted_events = convert_event_to_a2a_events(
                        adk_event,
                        invocation_context,
                        context.task_id,
                        context.context_id,
                        self._config.gen_ai_part_converter,
                    )
                    await self._enqueue_events(event_queue, task_result_aggregator, converted_events)
        finally:
            self._emitted_progress.pop(task_id, None)

        await self._publish_final_events(context, event_queue, task_result_aggregator)

    async def _enqueue_events(
        self,
        queue: EventQueue,
        aggregator: TaskResultAggregator,
        events: Iterable[Any],
    ) -> None:
        for event in events:
            aggregator.process_event(event)
            await queue.enqueue_event(event)

    def _progress_events_from_adk_event(
        self,
        adk_event: Event,
        context: RequestContext,
        invocation_context: InvocationContext,
    ) -> Iterable[TaskStatusUpdateEvent]:
        task_id = context.task_id
        if not task_id:
            return []

        emitted = self._emitted_progress.setdefault(task_id, set())
        events: list[TaskStatusUpdateEvent] = []

        def maybe_emit(key: ProgressKey, *, call: Any | None = None) -> None:
            if key in emitted:
                return
            label = self._label_for(
                key,
                invocation_context=invocation_context,
                call=call,
            )
            if not label:
                return
            emitted.add(key)
            events.append(
                TaskStatusUpdateEvent(
                    task_id=context.task_id,
                    status=TaskStatus(
                        state=TaskState.working,
                        timestamp=datetime.now(UTC).isoformat(),
                        message=self._build_message(label),
                    ),
                    context_id=context.context_id,
                    final=False,
                    metadata=_get_context_metadata(adk_event, invocation_context),
                )
            )

        for function_call in adk_event.get_function_calls():
            maybe_emit(("call", function_call.name), call=function_call)

        for function_response in adk_event.get_function_responses():
            maybe_emit(("response", function_response.name), call=function_response)

        if adk_event.is_final_response():
            maybe_emit(("finalizing", None))

        return events

    async def _publish_final_events(
        self,
        context: RequestContext,
        queue: EventQueue,
        aggregator: TaskResultAggregator,
    ) -> None:
        if (
            aggregator.task_state == TaskState.working
            and aggregator.task_status_message is not None
            and aggregator.task_status_message.parts
        ):
            await queue.enqueue_event(
                TaskArtifactUpdateEvent(
                    task_id=context.task_id,
                    last_chunk=True,
                    context_id=context.context_id,
                    artifact=Artifact(
                        artifact_id=str(uuid4()),
                        parts=aggregator.task_status_message.parts,
                    ),
                )
            )
            await queue.enqueue_event(
                TaskStatusUpdateEvent(
                    task_id=context.task_id,
                    status=TaskStatus(
                        state=TaskState.completed,
                        timestamp=datetime.now(UTC).isoformat(),
                    ),
                    context_id=context.context_id,
                    final=True,
                )
            )
        else:
            await queue.enqueue_event(
                TaskStatusUpdateEvent(
                    task_id=context.task_id,
                    status=TaskStatus(
                        state=aggregator.task_state,
                        timestamp=datetime.now(UTC).isoformat(),
                        message=aggregator.task_status_message,
                    ),
                    context_id=context.context_id,
                    final=True,
                )
            )

    def _label_for(
        self,
        key: ProgressKey,
        *,
        invocation_context: InvocationContext | None = None,
        call: Any | None = None,
    ) -> str | None:
        if key in self._progress_labels:
            return self._progress_labels[key]

        phase, name = key
        if phase in {"call", "response"} and name:
            friendly = name
            caller = self._resolve_invoker_name(invocation_context)

            if phase == "call":
                if caller:
                    return f"{caller}가 {friendly} 에이전트를 호출합니다."
                return f"{friendly} 에이전트를 호출합니다."

            if phase == "response":
                if caller:
                    return f"{friendly} 에이전트가 {caller}에 응답했습니다."
                return f"{friendly} 에이전트의 응답을 받았습니다."

        return None

    @staticmethod
    def _resolve_invoker_name(invocation_context: InvocationContext | None) -> str | None:
        """Extract a human-friendly name for the invoking agent/tool."""

        if invocation_context is None:
            return None

        for attr in ("agent_name", "agent_id", "agent"):
            value = getattr(invocation_context, attr, None)
            if isinstance(value, str) and value.strip():
                return value
        agent = getattr(invocation_context, "agent", None)
        # Some implementations expose the agent object directly.
        for attr in ("name", "agent_name"):
            candidate = getattr(agent, attr, None)
            if isinstance(candidate, str) and candidate.strip():
                return candidate

        return None

    def _build_message(self, text: str | None) -> Message | None:
        if not text:
            return None
        return Message(
            message_id=str(uuid4()),
            role=Role.agent,
            parts=[TextPart(text=text)],
        )


def _get_adk_metadata_key(key: str) -> str:
    return f"adk:{key}"


def _get_context_metadata(event: Event, invocation_context: InvocationContext) -> dict[str, Any]:
    metadata: dict[str, Any] = {}
    if invocation_context.app_name:
        metadata[_get_adk_metadata_key("app_name")] = invocation_context.app_name
    if invocation_context.session and invocation_context.session.id:
        metadata[_get_adk_metadata_key("session_id")] = invocation_context.session.id
    if invocation_context.user_id:
        metadata[_get_adk_metadata_key("user_id")] = invocation_context.user_id
    if event.id:
        metadata[_get_adk_metadata_key("event_id")] = event.id
    return metadata
