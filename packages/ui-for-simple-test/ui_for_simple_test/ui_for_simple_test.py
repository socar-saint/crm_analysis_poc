"""챗봇 테스트 UI"""

import inspect
import traceback
from typing import Any
from uuid import uuid4

import httpx
import reflex as rx
from a2a.client import A2ACardResolver, ClientConfig, ClientFactory
from a2a.types import Message, Role, TextPart
from reflex.event import PointerEventInfo

# UI 자체 설정
from .settings import settings

# 로컬 유틸리티 import
from .text_utils import extract_response_models_from_task, get_human_text_from_response


async def _execute_single_turn_request(message: str, agent_url: str) -> Any:
    """Send a single message to the orchestrator and return the task."""

    async with httpx.AsyncClient(timeout=httpx.Timeout(1200)) as httpx_client:
        card_resolver = A2ACardResolver(httpx_client=httpx_client, base_url=agent_url)
        card = await card_resolver.get_agent_card()
        client_config = ClientConfig(httpx_client=httpx_client, streaming=False)
        factory = ClientFactory(config=client_config)
        client = factory.create(card=card)

        request = Message(
            message_id=str(uuid4()),
            role=Role.user,
            parts=[TextPart(text=message)],
        )

        result = client.send_message(request)
        return await _resolve_task_from_result(result)


async def _resolve_task_from_result(result: Any) -> Any:
    """Normalise streaming/non-streaming responses into a task object."""

    if inspect.isasyncgen(result):
        last_event: Any = None
        async for event in result:
            last_event = event
        resolved = last_event
    else:
        resolved = await result

    if isinstance(resolved, tuple | list):
        return resolved[0]
    return resolved


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


class State(rx.State):
    """The app state."""

    # 메시지 리스트 [{"role": "user" or "assistant", "content": "메시지 내용"}]
    messages: list[dict[str, str]] = []

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

        try:
            task = await _execute_single_turn_request(user_message, self.agent_url)
            bot_response = _extract_human_text_from_task(task) or "응답을 받지 못했습니다."
        except Exception as exc:  # pragma: no cover - surfaced via UI
            traceback.print_exc()
            self._handle_failure_state()
            bot_response = f"오류가 발생했습니다: {str(exc)}\n에이전트 서버가 실행 중인지 확인해주세요."

        self._finish_interaction(bot_response)

    def _start_interaction(self, user_message: str) -> None:
        self.messages.append({"role": "user", "content": user_message})
        self.current_message = ""
        self.is_loading = True
        self.is_connected = True
        self.connection_status = "세션 활성"

    def _finish_interaction(self, bot_response: str) -> None:
        self.messages.append({"role": "assistant", "content": bot_response})
        self.is_loading = False

    def _handle_failure_state(self) -> None:
        self.is_connected = False
        self.connection_status = "세션 없음"

    def clear_messages(self) -> None:
        """대화 내역을 초기화하고 세션을 종료합니다."""
        self.messages = []
        self.is_connected = False
        self.connection_status = "세션 없음"

    def toggle_dark_mode(self) -> None:
        """다크모드를 토글합니다."""
        self.is_dark_mode = not self.is_dark_mode


def typing_indicator() -> rx.Component:
    """AI가 답변 중일 때 표시되는 타이핑 인디케이터"""
    return rx.box(
        rx.hstack(
            rx.box(
                rx.icon(
                    "bot",
                    size=20,
                    color="white",
                ),
                background="#3b82f6",
                padding="8px",
                border_radius="50%",
                box_shadow="0 2px 4px rgba(59, 130, 246, 0.2)",
            ),
            rx.box(
                rx.text(
                    "AI가 답변 중입니다...",
                    color=rx.cond(State.is_dark_mode, "#ffffff", "#000000"),
                    font_size="15px",
                    line_height="1.5",
                    font_weight="400",
                ),
                background=rx.cond(State.is_dark_mode, "#374151", "#f9f9f9"),
                padding="12px 16px",
                border_radius="12px",
                max_width="600px",
                box_shadow=rx.cond(
                    State.is_dark_mode, "0 1px 2px rgba(0, 0, 0, 0.3)", "0 1px 2px rgba(0, 0, 0, 0.05)"
                ),
                border=rx.cond(State.is_dark_mode, "1px solid #4b5563", "1px solid #d1d5db"),
            ),
            rx.box(),
            spacing="3",
            align="start",
            justify="start",
        ),
        width="100%",
        margin_bottom="16px",
    )


def message_box(message: dict[str, str]) -> rx.Component:
    """개별 메시지를 표시하는 컴포넌트 - 이미지와 동일한 디자인"""
    is_user = message["role"] == "user"

    return rx.cond(
        is_user,
        # 사용자 메시지 - 오른쪽에 연한 회색 배경
        rx.box(
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
        ),
        # AI 메시지 - 왼쪽에 투명(흰색) 배경
        rx.box(
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
        ),
    )


def header() -> rx.Component:
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


def chat_header() -> rx.Component:
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


def recommended_question_button(question: str) -> rx.Component:
    """추천 질문을 전송하는 버튼 - 심플한 텍스트 링크 스타일."""
    return rx.button(
        rx.cond(question.length() > 30, question[:27] + "...", question),  # type: ignore
        on_click=State.send_message(question),  # type: ignore
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


def recommended_questions_section() -> rx.Component:
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


def index() -> rx.Component:
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
                            rx.cond(
                                State.is_loading,
                                typing_indicator(),
                                rx.box(),
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

app.add_page(index)
