"""챗봇 테스트 UI"""

import inspect
import json
import time
import traceback
from collections.abc import AsyncIterator
from typing import Any
from urllib.parse import urlparse, urlunparse
from uuid import uuid4

import httpx
import reflex as rx
from a2a.client import A2ACardResolver, ClientConfig, ClientFactory
from a2a.types import Message, Role, TextPart
from reflex.components.component import Component
from reflex.event import PointerEventInfo
from reflex.state import State as ReflexState

# UI 자체 설정
from .settings import settings

# 로컬 유틸리티 import
from .text_utils import extract_response_models_from_task, get_human_text_from_response

FALLBACK_PROGRESS_MESSAGE = "에이전트가 작업을 진행 중입니다..."
PROCESS_LOG_TTL_SECONDS = 300


def _normalise_task_payload(value: Any) -> Any:
    """Handle tuple/list wrappers that some transports emit."""
    if isinstance(value, list | tuple):
        return value[0] if value else None
    return value


async def _stream_single_turn_request(message: str, agent_url: str) -> AsyncIterator[Any]:
    """Yield task snapshots as they stream back from the orchestrator."""

    async with httpx.AsyncClient(timeout=httpx.Timeout(1200)) as httpx_client:
        card_resolver = A2ACardResolver(httpx_client=httpx_client, base_url=agent_url)
        card = await card_resolver.get_agent_card()
        # Override host/port advertised in the card so design-time UI can talk to local servers.
        base = urlparse(agent_url)

        def _with_local_host(target_url: str) -> str:
            parsed = urlparse(target_url)
            # Preserve original path/query while forcing scheme+host from the design-time base URL.
            updated = parsed._replace(
                scheme=base.scheme or parsed.scheme,
                netloc=base.netloc or parsed.netloc,
            )
            return urlunparse(updated)

        try:
            card.url = _with_local_host(card.url)
            additional = getattr(card, "additional_interfaces", None) or []
            for interface in additional:
                interface.url = _with_local_host(interface.url)
        except Exception:
            # Fallback in case the card implementation is not mutable: use minimal card limited to primary URL.
            from a2a.client import minimal_agent_card

            transports = [card.preferred_transport] if getattr(card, "preferred_transport", None) else None
            card = minimal_agent_card(
                url=_with_local_host(card.url),
                transports=transports,
            )

        client_config = ClientConfig(httpx_client=httpx_client, streaming=True)
        factory = ClientFactory(config=client_config)
        client = factory.create(card=card)

        request = Message(
            message_id=str(uuid4()),
            role=Role.user,
            parts=[TextPart(text=message)],
        )

        result = client.send_message(request)

        if inspect.isasyncgen(result):
            async for event in result:
                payload = _normalise_task_payload(event)
                if payload is not None:
                    yield payload
            return

        resolved = await result
        payload = _normalise_task_payload(resolved)
        if payload is not None:
            yield payload


def _extract_human_text_from_task(task: Any) -> str:
    """Return human-readable text from a task payload."""

    responses = extract_response_models_from_task(task)
    if responses:
        last_resp = responses[-1].model_dump()
        human_text = get_human_text_from_response(last_resp).strip()
        if human_text:
            return human_text

    return _latest_agent_text(task)


def _latest_agent_text(task: Any) -> str:
    """Fallback to the agent's latest free-form text message."""

    history = getattr(task, "history", None) or []
    for message in reversed(history):
        role = getattr(message, "role", None)
        if role != Role.agent:
            continue

        parts = getattr(message, "parts", None) or []
        texts: list[str] = []
        for part in parts:
            root = getattr(part, "root", part)
            if getattr(root, "kind", None) != "text":
                continue
            text = getattr(root, "text", "")
            if isinstance(text, str):
                stripped = text.strip()
                if stripped:
                    texts.append(stripped)

        if texts:
            return "\n".join(texts)

    return ""


def _stringify_part_content(part: Any) -> str | None:
    """Best-effort conversion of task part payloads into readable text."""

    root = getattr(part, "root", part)

    text = getattr(root, "text", None)
    if isinstance(text, str):
        stripped = text.strip()
        if stripped:
            return stripped

    data = getattr(root, "data", None)
    if isinstance(data, dict):
        for key in ("status", "message", "content", "detail", "log", "text"):
            value = data.get(key)
            if isinstance(value, str) and (value := value.strip()):
                return value
        try:
            return json.dumps(data, ensure_ascii=False)
        except TypeError:
            return str(data)

    content = getattr(root, "content", None)
    if isinstance(content, str) and (content := content.strip()):
        return content

    # Fallback to repr for unknown payloads
    repr_text = repr(root)
    return repr_text if repr_text else None


def _extract_process_history(task: Any) -> list[dict[str, str]]:
    """Pull log-style entries from task.history."""

    history = getattr(task, "history", None) or []
    logs: list[dict[str, str]] = []

    for message in history:
        role = getattr(message, "role", None)
        role_value: str
        if hasattr(role, "value"):
            role_value = str(role.value)  # type: ignore
        elif isinstance(role, str):
            role_value = role
        else:
            role_value = str(role or "unknown")

        role_label = role_value.split(".")[-1] if "." in role_value else role_value
        role_label = role_label or "unknown"
        normalized_role = role_label.lower()

        if normalized_role in {"user", "agent"}:
            continue

        parts = getattr(message, "parts", None) or []
        texts: list[str] = []
        for part in parts:
            text = _stringify_part_content(part)
            if text:
                texts.append(text)

        if texts:
            logs.append({"label": role_label.upper(), "content": "\n".join(texts)})

    return logs


def _extract_artifact_logs(task: Any) -> list[dict[str, str]]:
    """Extract log-like entries from task artifacts if present."""

    artifacts = getattr(task, "artifacts", None) or []
    logs: list[dict[str, str]] = []

    for artifact in artifacts:
        label = getattr(artifact, "kind", None) or getattr(artifact, "name", None) or "ARTIFACT"
        parts = getattr(artifact, "parts", None) or []
        texts: list[str] = []
        for part in parts:
            text = _stringify_part_content(part)
            if text:
                texts.append(text)
        if texts:
            logs.append({"label": str(label).upper(), "content": "\n".join(texts)})

    return logs


def _stringify_event_payload(event: Any) -> str | None:
    """Convert a streaming event payload into display-friendly text."""

    if event is None:
        return None

    status_text = _event_status_text(event)
    if status_text:
        return status_text

    data = _event_payload_dict(event)
    if data:
        dict_text = _string_from_mapping(data)
        if dict_text:
            return dict_text

    return _fallback_event_text(event)


def _event_status_text(event: Any) -> str | None:
    """Extract status.message text strings from an event, if available."""
    status = getattr(event, "status", None)
    if status is None:
        return None
    message = getattr(status, "message", None)
    parts = getattr(message, "parts", None) or []
    texts = [text for part in parts if (text := _stringify_part_content(part))]
    return "\n".join(texts) if texts else None


def _event_payload_dict(event: Any) -> dict[str, Any] | None:
    """Return a mapping representation from dataclass/pydantic events."""
    dump = getattr(event, "model_dump", None)
    data: Any = None
    if callable(dump):
        try:
            data = dump()
        except Exception:
            data = None
    if not isinstance(data, dict):
        data = getattr(event, "__dict__", None)
    return data if isinstance(data, dict) else None


def _string_from_mapping(data: dict[str, Any]) -> str | None:
    """Pull a human-friendly string from a mapping of event data."""
    for key in ("status", "message", "content", "detail", "text"):
        value = data.get(key)
        if isinstance(value, str) and (value := value.strip()):
            return value
    try:
        return json.dumps(data, ensure_ascii=False)
    except TypeError:
        return None


def _fallback_event_text(event: Any) -> str | None:
    """Best effort fallback string conversion for arbitrary event objects."""
    if isinstance(event, str):
        stripped = event.strip()
        if stripped:
            return stripped
    text = getattr(event, "text", None)
    if isinstance(text, str) and (text := text.strip()):
        return text
    return repr(event)


def _label_from_event(event: Any) -> str:
    """Derive a readable label from the event object."""

    if hasattr(event, "label"):
        label = event.label
    elif hasattr(event, "kind"):
        label = event.kind
    elif hasattr(event, "type"):
        label = event.type
    else:
        label = event.__class__.__name__

    if isinstance(label, str) and label:
        return label.upper()
    return "EVENT"


def _merge_log_entries(existing: list[dict[str, str]], new_entries: list[dict[str, str]]) -> list[dict[str, str]]:
    """Merge two log lists while preserving order and removing duplicates."""

    merged: list[dict[str, str]] = []
    seen: set[tuple[str, str]] = set()

    def _add(entry: dict[str, str]) -> None:
        key = (entry.get("label", ""), entry.get("content", ""))
        if key in seen or not entry.get("content"):
            return
        seen.add(key)
        merged.append(entry)

    for entry in existing:
        _add(entry)
    for entry in new_entries:
        _add(entry)

    return merged


def _extract_process_logs(snapshot: Any) -> list[dict[str, str]]:
    """Return log-friendly entries from streaming snapshots or completed tasks."""

    # TaskUpdate objects expose .task/.event; dictionaries mimic that too.
    task = snapshot
    event = None

    if isinstance(snapshot, dict):
        task = snapshot.get("task", snapshot)
        event = snapshot.get("event")
    else:
        event = getattr(snapshot, "event", None)
        task = getattr(snapshot, "task", snapshot)

    logs = _extract_process_history(task)
    logs.extend(_extract_artifact_logs(task))

    event_entry: dict[str, str] | None = None
    if event is not None:
        event_text = _stringify_event_payload(event)
        if event_text:
            event_entry = {"label": _label_from_event(event), "content": event_text}

    if event_entry is None and hasattr(snapshot, "status"):
        status = getattr(snapshot, "status", None)
        status_label = getattr(status, "state", None)
        label = str(status_label).split(".")[-1] if status_label else "STATUS"
        status_text = _stringify_event_payload(snapshot)
        if status_text:
            event_entry = {"label": label.upper(), "content": status_text}

    if event_entry:
        logs.append(event_entry)

    # Deduplicate while preserving order so repeated streaming snapshots don't grow indefinitely.
    seen: set[tuple[str, str]] = set()
    unique_logs: list[dict[str, str]] = []
    for entry in logs:
        key = (entry.get("label", ""), entry.get("content", ""))
        if key in seen or not entry.get("content"):
            continue
        seen.add(key)
        unique_logs.append(entry)

    return unique_logs


class State(ReflexState):
    """The app state."""

    # 메시지 리스트 [{"role": "user" or "assistant", "content": "메시지 내용"}]
    messages: list[dict[str, Any]] = []

    # 현재 입력 중인 메시지
    current_message: str = ""

    # 로딩 상태
    is_loading: bool = False

    # 에이전트 URL
    agent_url: str = settings.orchestrator_base_url

    # 연결 상태 (세션 활성화 여부)
    is_connected: bool = False
    connection_status: str = "세션 없음"
    recommended_questions: list[str] = settings.recommended_questions

    # 다크모드 상태
    is_dark_mode: bool = False

    # 에이전트 진행 로그 [{"label": "TOOL", "content": "..."}]
    process_logs: list[dict[str, str]] = []
    process_logs_collapsed: bool = False
    process_logs_expiration: float | None = None

    # 현재 실행 중인 태스크 (직렬화 가능한 형태로 저장)
    current_task_data: dict[str, Any] | None = None

    def set_current_message(self, message: str) -> None:
        """현재 메시지를 설정합니다."""
        self.current_message = message

    async def send_message(
        self,
        event_or_message: PointerEventInfo | str | None = None,
    ) -> None:
        """사용자 메시지를 전송하고 봇 응답을 받습니다."""
        if isinstance(event_or_message, str):
            self.current_message = event_or_message

        if not self.current_message.strip():
            return

        user_message = self.current_message
        self._start_interaction(user_message)

        # 상태 업데이트를 강제로 반영
        yield

        task: Any | None = None
        try:
            async for snapshot in _stream_single_turn_request(user_message, self.agent_url):
                if self._handle_snapshot_update(snapshot):
                    yield

            if self.current_task_data:
                task = self.current_task_data.get("task")
            bot_response = _extract_human_text_from_task(task) or "응답을 받지 못했습니다."
        except Exception as exc:  # pragma: no cover - surfaced via UI
            bot_response = self._handle_stream_error(exc)

        self._finish_interaction(bot_response, task)

    def _start_interaction(self, user_message: str) -> None:
        self._maybe_clear_expired_process_logs()
        updated_messages: list[dict[str, Any]] = []
        for entry in self.messages:
            if entry.get("show_progress_after"):
                new_entry = {**entry}
                new_entry["show_progress_after"] = False
                updated_messages.append(new_entry)
            else:
                updated_messages.append(entry)
        updated_messages.append(
            {
                "role": "user",
                "content": user_message,
                "show_progress_after": True,
            }
        )
        self.messages = updated_messages
        self.current_message = ""
        self.is_loading = True
        self.is_connected = True
        self.connection_status = "세션 활성"
        self.current_task_data = None
        self.process_logs = []
        self.process_logs_collapsed = False
        self.process_logs_expiration = None

    def _finish_interaction(self, bot_response: str, task: Any | None = None) -> None:
        self.messages.append({"role": "assistant", "content": bot_response})
        self.is_loading = False
        if any(entry.get("label") == "ERROR" for entry in self.process_logs):
            self.process_logs_collapsed = False
            self.process_logs_expiration = None
            return
        if self.process_logs:
            self.process_logs_collapsed = True
            self.process_logs_expiration = time.time() + PROCESS_LOG_TTL_SECONDS
        else:
            self.process_logs_collapsed = False
            self.process_logs_expiration = None

    def _handle_snapshot_update(self, snapshot: Any) -> bool:
        """Update state from a streaming snapshot; return True if UI should refresh."""
        updated = False
        if snapshot is not None:
            self.current_task_data = {"task": snapshot}
            updated = True

        logs = _extract_process_logs(snapshot)
        if logs:
            existing = [entry for entry in self.process_logs if entry.get("content") != FALLBACK_PROGRESS_MESSAGE]
            merged = _merge_log_entries(existing, logs)
            if merged != self.process_logs:
                self.process_logs = merged
                self.process_logs_collapsed = False
                self.process_logs_expiration = None
                updated = True
        else:
            updated = self._ensure_progress_placeholder() or updated

        return updated

    def _ensure_progress_placeholder(self) -> bool:
        """Insert a default progress message when no logs are available."""
        if self.process_logs:
            return False
        self.process_logs = [
            {
                "label": "STATUS",
                "content": FALLBACK_PROGRESS_MESSAGE,
            }
        ]
        self.process_logs_collapsed = False
        self.process_logs_expiration = None
        return True

    def _handle_stream_error(self, exc: Exception) -> str:
        """Record an error state and return a user-facing message."""
        traceback.print_exc()
        self.process_logs = [
            {
                "label": "ERROR",
                "content": f"에이전트 호출 중 오류 발생: {str(exc)}",
            }
        ]
        self.process_logs_collapsed = False
        self.process_logs_expiration = None
        self._handle_failure_state()
        return f"오류가 발생했습니다: {str(exc)}\n에이전트 서버가 실행 중인지 확인해주세요."

    def _handle_failure_state(self) -> None:
        self.is_connected = False
        self.connection_status = "세션 없음"

    def _maybe_clear_expired_process_logs(self) -> None:
        """Remove stored process logs once their TTL has elapsed."""
        if self.process_logs_expiration is None:
            return
        if time.time() < self.process_logs_expiration:
            return
        self.process_logs = []
        self.process_logs_collapsed = False
        self.process_logs_expiration = None

    def toggle_process_logs(self) -> None:
        """Toggle visibility of the most recent agent progress panel."""
        self._maybe_clear_expired_process_logs()
        if not self.process_logs:
            return
        self.process_logs_collapsed = not self.process_logs_collapsed

    def clear_messages(self) -> None:
        """대화 내역을 초기화하고 세션을 종료합니다."""
        self.messages = []
        self.is_connected = False
        self.connection_status = "세션 없음"
        self.is_loading = False
        self.process_logs = []
        self.process_logs_collapsed = False
        self.process_logs_expiration = None
        self.current_task_data = None

    def toggle_dark_mode(self) -> None:
        """다크모드를 토글합니다."""
        self.is_dark_mode = not self.is_dark_mode


def message_box(message: dict[str, Any]) -> Component:
    """개별 메시지를 표시하는 컴포넌트 - 이미지와 동일한 디자인"""
    is_user = message["role"] == "user"
    show_progress_after = message.get("show_progress_after", False)

    user_message = rx.box(
        rx.text(
            message["content"],
            color=rx.cond(State.is_dark_mode, "#ffffff", "#111827"),
            font_size="15px",
            font_weight="400",
            line_height="1.5",
        ),
        background=rx.cond(State.is_dark_mode, "#374151", "#f3f4f6"),
        padding="12px 16px",
        border_radius="8px",
        max_width="600px",
        margin_left="auto",
        margin_bottom="16px",
        box_shadow=rx.cond(State.is_dark_mode, "0 1px 2px rgba(0, 0, 0, 0.3)", "0 1px 2px rgba(0, 0, 0, 0.05)"),
        border=rx.cond(State.is_dark_mode, "1px solid #4b5563", "1px solid #e5e7eb"),
    )

    assistant_message = rx.box(
        rx.text(
            message["content"],
            color=rx.cond(State.is_dark_mode, "#ffffff", "#111827"),
            font_size="15px",
            line_height="1.5",
            font_weight="400",
        ),
        background=rx.cond(State.is_dark_mode, "#374151", "#ffffff"),
        padding="12px 16px",
        border_radius="8px",
        max_width="600px",
        margin_bottom="16px",
        box_shadow=rx.cond(State.is_dark_mode, "0 1px 2px rgba(0, 0, 0, 0.3)", "0 1px 2px rgba(0, 0, 0, 0.05)"),
        border=rx.cond(State.is_dark_mode, "1px solid #4b5563", "none"),
    )

    return rx.cond(
        is_user,
        rx.vstack(
            user_message,
            rx.cond(
                show_progress_after,
                process_logs_panel(),
                rx.box(),
            ),
            spacing="2",
            width="100%",
            align="stretch",
        ),
        assistant_message,
    )


def process_log_entry(entry: dict[str, str]) -> Component:
    """에이전트 진행 로그 한 항목을 렌더링."""
    label = entry.get("label", "LOG")
    content = entry.get("content", "")

    # 현재 진행 단계에 따른 시각적 효과
    is_current_step = (label == "STATUS") & State.is_loading
    accent_color = rx.cond(State.is_dark_mode, "#60a5fa", "#2563eb")
    label_color = rx.cond(State.is_dark_mode, "#9ca3af", "#6b7280")
    text_color = rx.cond(State.is_dark_mode, "#e5e7eb", "#1f2937")

    return rx.box(
        rx.vstack(
            rx.hstack(
                rx.text(
                    label,
                    font_size="11px",
                    font_weight="600",
                    letter_spacing="0.5px",
                    color=label_color,
                    text_transform="uppercase",
                ),
                rx.cond(
                    is_current_step,
                    rx.icon("dot", color=accent_color, size=10),
                    rx.box(width="10px"),
                ),
                align="center",
                width="100%",
            ),
            rx.text(
                content,
                font_size="13px",
                line_height="1.6",
                color=text_color,
                style={"white_space": "pre-wrap"},
            ),
            spacing="1",
            align="start",
        ),
        width="100%",
        padding="8px 12px",
        border_left=rx.cond(is_current_step, f"2px solid {accent_color}", "2px solid transparent"),
        border_radius="6px",
    )


def process_logs_panel() -> Component:
    """에이전트 진행 로그 전체 패널."""
    return rx.cond(
        State.process_logs.length() == 0,  # type: ignore
        rx.box(),
        rx.box(
            rx.vstack(
                rx.hstack(
                    rx.text(
                        "Agent Progress",
                        font_size="12px",
                        font_weight="600",
                        letter_spacing="1px",
                        color=rx.cond(State.is_dark_mode, "#9ca3af", "#4b5563"),
                        text_transform="uppercase",
                    ),
                    rx.box(flex="1"),
                    rx.button(
                        rx.hstack(
                            rx.text(
                                rx.cond(
                                    State.process_logs_collapsed,
                                    "Show",
                                    "Hide",
                                ),
                                font_size="12px",
                                font_weight="500",
                                color=rx.cond(State.is_dark_mode, "#9ca3af", "#4b5563"),
                            ),
                            rx.icon(
                                rx.cond(
                                    State.process_logs_collapsed,
                                    "chevron-down",
                                    "chevron-up",
                                ),
                                size=16,
                            ),
                            spacing="1",
                            align="center",
                        ),
                        on_click=State.toggle_process_logs,
                        variant="ghost",
                        style={
                            "background": "transparent",
                            "border": "none",
                            "padding": "4px 6px",
                            "border_radius": "6px",
                            "cursor": "pointer",
                            "_hover": {
                                "background": rx.cond(State.is_dark_mode, "#374151", "#f3f4f6"),
                            },
                        },
                    ),
                    align="center",
                    width="100%",
                ),
                rx.cond(
                    State.process_logs_collapsed,
                    rx.box(),
                    rx.vstack(
                        rx.foreach(State.process_logs, process_log_entry),
                        spacing="2",
                        width="100%",
                    ),
                ),
                spacing="3",
                align="start",
                width="100%",
            ),
            width="100%",
            padding="12px 16px",
            margin_bottom="16px",
            border_radius="10px",
            background=rx.cond(State.is_dark_mode, "#1f2937", "#ffffff"),
            border=rx.cond(State.is_dark_mode, "1px solid #374151", "1px solid #e5e7eb"),
            box_shadow="none",
        ),
    )


def header() -> Component:
    """상단 헤더 컴포넌트 - GitHub 링크와 다크모드 토글"""
    return rx.box(
        rx.hstack(
            # 왼쪽 GitHub 링크
            rx.box(
                rx.link(
                    rx.text(
                        "socar-inc/ai-agent-platform",
                        font_size="14px",
                        font_weight="500",
                        color=rx.cond(State.is_dark_mode, "#ffffff", "#000000"),
                    ),
                    href="https://github.com/socar-inc/ai-agent-platform",
                    target="_blank",
                    style={
                        "text_decoration": "none",
                        "_hover": {
                            "text_decoration": "underline",
                        },
                    },
                ),
                background=rx.cond(State.is_dark_mode, "#1a1a1a", "#f3f4f6"),
                padding="8px 12px",
                border_radius="6px",
            ),
            rx.box(flex="1"),  # 오른쪽 공간 채우기
            # 다크모드 토글 버튼
            rx.button(
                rx.icon(
                    rx.cond(State.is_dark_mode, "sun", "moon"),
                    size=20,
                ),
                on_click=State.toggle_dark_mode,
                variant="ghost",
                style={
                    "background": "transparent",
                    "border": "none",
                    "padding": "8px",
                    "border_radius": "8px",
                    "cursor": "pointer",
                    "_hover": {
                        "background": rx.cond(State.is_dark_mode, "#374151", "#f3f4f6"),
                    },
                },
            ),
            justify="between",
            align="center",
            width="100%",
            padding="16px 24px",
            background=rx.cond(State.is_dark_mode, "#1a1a1a", "#ffffff"),
        ),
    )


def chat_header() -> Component:
    """채팅 화면용 헤더 컴포넌트 - New Chat 버튼과 다크모드 토글"""
    return rx.box(
        rx.hstack(
            rx.box(flex="1"),  # 왼쪽 공간 채우기
            # New Chat 버튼
            rx.button(
                rx.text(
                    "New Chat",
                    font_size="14px",
                    font_weight="500",
                    color=rx.cond(State.is_dark_mode, "#ffffff", "#000000"),
                ),
                on_click=State.clear_messages,
                variant="ghost",
                style={
                    "background": "transparent",
                    "border": "none",
                    "padding": "8px 12px",
                    "border_radius": "6px",
                    "cursor": "pointer",
                    "_hover": {
                        "background": rx.cond(State.is_dark_mode, "#374151", "#f3f4f6"),
                    },
                },
            ),
            # 다크모드 토글 버튼
            rx.button(
                rx.icon(
                    rx.cond(State.is_dark_mode, "sun", "moon"),
                    size=20,
                ),
                on_click=State.toggle_dark_mode,
                variant="ghost",
                style={
                    "background": "transparent",
                    "border": "none",
                    "padding": "8px",
                    "border_radius": "8px",
                    "cursor": "pointer",
                    "_hover": {
                        "background": rx.cond(State.is_dark_mode, "#374151", "#f3f4f6"),
                    },
                },
            ),
            justify="between",
            align="center",
            width="100%",
            padding="16px 24px",
            background=rx.cond(State.is_dark_mode, "#1a1a1a", "#ffffff"),
        ),
    )


def recommended_question_button(question: str) -> Component:
    """추천 질문을 전송하는 버튼 - 심플한 텍스트 링크 스타일."""
    return rx.button(
        rx.cond(question.length() > 30, question[:27] + "...", question),  # type: ignore
        on_click=lambda: State.send_message(question),  # type: ignore
        disabled=State.is_loading,
        variant="ghost",
        title=question,  # 전체 텍스트를 툴팁으로 표시
        style={
            "background": "transparent",
            "border": "none",
            "padding": "8px 12px",
            "font_size": "16px",
            "font_weight": "400",
            "color": rx.cond(State.is_dark_mode, "#9ca3af", "#6b7280"),
            "text_align": "left",
            "cursor": "pointer",
            "border_radius": "4px",
            "transition": "all 0.2s ease",
            "max_width": "300px",
            "white_space": "nowrap",
            "overflow": "hidden",
            "text_overflow": "ellipsis",
            "font_family": "monospace",
            "letter_spacing": "0.5px",
            "_hover": {
                "background": rx.cond(State.is_dark_mode, "#374151", "#f3f4f6"),
                "color": rx.cond(State.is_dark_mode, "#ffffff", "#374151"),
            },
            "_active": {
                "background": rx.cond(State.is_dark_mode, "#4b5563", "#e5e7eb"),
                "color": rx.cond(State.is_dark_mode, "#ffffff", "#111827"),
            },
        },
    )


def recommended_questions_section() -> Component:
    """입력 영역 아래에 표시되는 추천 질문 목록 - 심플한 스타일."""
    return rx.cond(
        State.recommended_questions.length() == 0,  # type: ignore
        rx.box(),
        rx.flex(
            rx.foreach(
                State.recommended_questions,
                recommended_question_button,
            ),
            direction="row",
            gap="24px",
            wrap="wrap",
            justify="center",
            width="100%",
            max_width="800px",
            margin_top="32px",
        ),
    )


def index() -> Component:
    """챗봇 UI 메인 페이지"""
    return rx.box(
        rx.vstack(
            # 상단 헤더 (초기 화면에서는 GitHub 링크, 채팅 화면에서는 다크모드 토글만)
            rx.cond(
                State.messages.length() == 0,  # type: ignore
                header(),
                chat_header(),
            ),
            # 메인 콘텐츠 영역
            rx.box(
                rx.cond(
                    State.messages.length() == 0,  # type: ignore
                    # 초기 화면
                    rx.center(
                        rx.vstack(
                            rx.text(
                                "What would you like to know?",
                                font_size="24px",
                                font_weight="600",
                                color=rx.cond(State.is_dark_mode, "#ffffff", "#111827"),
                                margin_bottom="48px",
                                text_align="center",
                                font_family="monospace",
                                letter_spacing="0.5px",
                            ),
                            # 중앙 검색창
                            rx.box(
                                rx.vstack(
                                    rx.box(
                                        rx.hstack(
                                            rx.text_area(
                                                placeholder="Ask me anything...",
                                                value=State.current_message,
                                                on_change=State.set_current_message,
                                                name="message_input",
                                                resize="none",
                                                width="100%",
                                                min_height="150px",
                                                max_height="200px",
                                                style={
                                                    "font_size": "16px",
                                                    "padding": "24px 100px 24px 32px",
                                                    "border_radius": "20px",
                                                    "border": rx.cond(
                                                        State.is_dark_mode, "2px solid #4b5563", "2px solid #e5e7eb"
                                                    ),
                                                    "background": rx.cond(State.is_dark_mode, "#374151", "#ffffff"),
                                                    "color": rx.cond(State.is_dark_mode, "#ffffff", "#111827"),
                                                    "outline": "none",
                                                    "font_family": "Inter, sans-serif",
                                                    "font_weight": "400",
                                                    "box_shadow": rx.cond(
                                                        State.is_dark_mode,
                                                        "0 4px 6px rgba(0, 0, 0, 0.3)",
                                                        "0 4px 6px rgba(0, 0, 0, 0.05)",
                                                    ),
                                                    "word_wrap": "break-word",
                                                    "white_space": "pre-wrap",
                                                    "_focus": {
                                                        "border_color": "#3b82f6",
                                                        "box_shadow": "0 0 0 4px rgba(59, 130, 246, 0.1)",
                                                    },
                                                    "::placeholder": {
                                                        "color": rx.cond(State.is_dark_mode, "#ffffff", "#9ca3af"),
                                                    },
                                                },
                                            ),
                                            rx.button(
                                                rx.icon("send", size=20),
                                                on_click=State.send_message,
                                                disabled=State.is_loading,
                                                variant="solid",
                                                style={
                                                    "background": "#111827",
                                                    "cursor": "pointer",
                                                    "height": "50px",
                                                    "width": "50px",
                                                    "border_radius": "12px",
                                                    "box_shadow": "0 2px 4px rgba(0, 0, 0, 0.1)",
                                                    "border": "none",
                                                    "position": "absolute",
                                                    "right": "12px",
                                                    "bottom": "12px",
                                                    "top": "auto",
                                                    "transform": "none",
                                                    "_hover": {
                                                        "background": "#374151",
                                                        "transform": "scale(1.05)",
                                                    },
                                                    "_active": {
                                                        "transform": "scale(0.95)",
                                                    },
                                                },
                                            ),
                                            spacing="0",
                                            width="100%",
                                            align="center",
                                            position="relative",
                                        ),
                                        width="100%",
                                        max_width="900px",
                                    ),
                                    spacing="0",
                                    align="center",
                                ),
                                width="100%",
                                margin_bottom="48px",
                            ),
                            # 추천 질문들
                            recommended_questions_section(),
                            spacing="0",
                            align="center",
                        ),
                        width="100%",
                        height="100%",
                    ),
                    # 채팅 화면
                    rx.box(
                        rx.vstack(
                            rx.foreach(
                                State.messages,
                                message_box,
                            ),
                            width="100%",
                            spacing="0",
                        ),
                        flex="1",
                        overflow_y="auto",
                        padding="24px",
                        background=rx.cond(State.is_dark_mode, "#1a1a1a", "#ffffff"),
                        width="100%",
                    ),
                ),
                flex="1",
                width="100%",
            ),
            # 하단 입력 영역 (메시지가 있을 때만 표시)
            rx.cond(
                State.messages.length() > 0,  # type: ignore
                rx.box(
                    rx.vstack(
                        # 입력 필드
                        rx.box(
                            rx.hstack(
                                rx.text_area(
                                    placeholder="What would you like to know?",
                                    value=State.current_message,
                                    on_change=State.set_current_message,
                                    name="message_input",
                                    resize="none",
                                    width="100%",
                                    min_height="60px",
                                    max_height="120px",
                                    style={
                                        "font_size": "16px",
                                        "padding": "16px 60px 16px 20px",
                                        "border_radius": "12px",
                                        "border": rx.cond(
                                            State.is_dark_mode, "1px solid #4b5563", "1px solid #e5e7eb"
                                        ),
                                        "background": rx.cond(State.is_dark_mode, "#374151", "#ffffff"),
                                        "color": rx.cond(State.is_dark_mode, "#ffffff", "#111827"),
                                        "outline": "none",
                                        "font_family": "Inter, sans-serif",
                                        "font_weight": "400",
                                        "box_shadow": rx.cond(
                                            State.is_dark_mode,
                                            "0 2px 4px rgba(0, 0, 0, 0.3)",
                                            "0 2px 4px rgba(0, 0, 0, 0.05)",
                                        ),
                                        "_focus": {
                                            "border_color": "#3b82f6",
                                            "box_shadow": "0 0 0 2px rgba(59, 130, 246, 0.1)",
                                        },
                                        "::placeholder": {
                                            "color": rx.cond(State.is_dark_mode, "#ffffff", "#9ca3af"),
                                        },
                                    },
                                ),
                                rx.button(
                                    rx.icon("send", size=20),
                                    on_click=State.send_message,
                                    disabled=State.is_loading,
                                    variant="solid",
                                    style={
                                        "background": "#111827",
                                        "cursor": "pointer",
                                        "height": "40px",
                                        "width": "40px",
                                        "border_radius": "8px",
                                        "box_shadow": "0 2px 4px rgba(0, 0, 0, 0.1)",
                                        "border": "none",
                                        "position": "absolute",
                                        "right": "10px",
                                        "bottom": "10px",
                                        "top": "auto",
                                        "transform": "none",
                                        "_hover": {
                                            "background": "#374151",
                                            "transform": "scale(1.05)",
                                        },
                                        "_active": {
                                            "transform": "scale(0.95)",
                                        },
                                    },
                                ),
                                spacing="0",
                                width="100%",
                                align="center",
                                position="relative",
                            ),
                            width="100%",
                            max_width="800px",
                        ),
                        spacing="0",
                        align="center",
                    ),
                    padding="24px",
                    background=rx.cond(State.is_dark_mode, "#1f2937", "#ffffff"),
                    border_top=rx.cond(State.is_dark_mode, "1px solid #374151", "1px solid #f3f4f6"),
                    width="100%",
                ),
                rx.box(),
            ),
            spacing="0",
            width="100%",
            height="100vh",
        ),
        width="100%",
        min_height="100vh",
        background=rx.cond(State.is_dark_mode, "#1a1a1a", "#ffffff"),
    )


app = rx.App(
    stylesheets=[
        "https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap",
    ],
    style={
        "font_family": "Inter, sans-serif",
        "background_color": "#ffffff",
    },
)

# CSS 애니메이션은 인라인 스타일로 처리

app.add_page(index)
