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
                background="linear-gradient(135deg, #667eea 0%, #764ba2 100%)",
                padding="8px",
                border_radius="50%",
                box_shadow="0 2px 8px rgba(102, 126, 234, 0.3)",
            ),
            rx.box(
                rx.text(
                    "AI가 답변 중입니다...",
                    color="#1a1a1a",
                    font_size="15px",
                    line_height="1.5",
                    font_weight="400",
                ),
                background="#f7f7f8",
                padding="12px 16px",
                border_radius="18px",
                max_width="600px",
                box_shadow="0 2px 4px rgba(0, 0, 0, 0.05)",
                border="1px solid #e5e7eb",
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
    """개별 메시지를 표시하는 컴포넌트"""
    is_user = message["role"] == "user"

    return rx.box(
        rx.hstack(
            rx.cond(
                ~is_user,
                rx.box(
                    rx.icon(
                        "bot",
                        size=20,
                        color="white",
                    ),
                    background="linear-gradient(135deg, #667eea 0%, #764ba2 100%)",
                    padding="8px",
                    border_radius="50%",
                    box_shadow="0 2px 8px rgba(102, 126, 234, 0.3)",
                ),
                rx.box(),
            ),
            rx.box(
                rx.text(
                    message["content"],
                    color=rx.cond(is_user, "white", "#1a1a1a"),
                    font_size="15px",
                    line_height="1.5",
                    font_weight="400",
                ),
                background=rx.cond(
                    is_user,
                    "linear-gradient(135deg, #667eea 0%, #764ba2 100%)",
                    "#f7f7f8",
                ),
                padding="12px 16px",
                border_radius="18px",
                max_width="600px",
                box_shadow=rx.cond(
                    is_user,
                    "0 2px 8px rgba(102, 126, 234, 0.25)",
                    "0 2px 4px rgba(0, 0, 0, 0.05)",
                ),
            ),
            rx.cond(
                is_user,
                rx.box(
                    rx.icon(
                        "user",
                        size=20,
                        color="white",
                    ),
                    background="linear-gradient(135deg, #10b981 0%, #059669 100%)",
                    padding="8px",
                    border_radius="50%",
                    box_shadow="0 2px 8px rgba(16, 185, 129, 0.3)",
                ),
                rx.box(),
            ),
            spacing="3",
            align="start",
            justify=rx.cond(is_user, "end", "start"),
        ),
        width="100%",
        margin_bottom="16px",
    )


def recommended_question_button(question: str) -> rx.Component:
    """추천 질문을 전송하는 버튼."""
    return rx.button(
        question,
        on_click=State.send_message(question),  # type: ignore
        disabled=State.is_loading,
        variant="soft",
        size="2",
        color_scheme="indigo",
        style={
            "border_radius": "9999px",
            "padding": "8px 14px",
            "font_weight": "500",
            "white_space": "normal",
            "width": "100%",
            "height": "auto",
            "min_height": "40px",
            "display": "flex",
            "align_items": "center",
            "justify_content": "center",
            "text_align": "center",
            "line_height": "1.2",
        },
    )


def recommended_questions_section() -> rx.Component:
    """입력 영역 위에 표시되는 추천 질문 목록."""
    return rx.cond(
        State.recommended_questions.length() == 0,  # type: ignore
        rx.box(),
        rx.vstack(
            rx.text(
                "추천 질문",
                font_size="14px",
                font_weight="600",
                color=rx.color("gray", 11),
            ),
            rx.flex(
                rx.foreach(
                    State.recommended_questions,
                    recommended_question_button,
                ),
                direction="column",
                gap="8px",
            ),
            spacing="2",
            align="start",
            width="100%",
        ),
    )


def index() -> rx.Component:
    """챗봇 UI 메인 페이지"""
    return rx.box(
        rx.center(
            rx.vstack(
                # 헤더
                rx.box(
                    rx.hstack(
                        rx.hstack(
                            rx.icon(
                                "bot",
                                size=28,
                                color="#667eea",
                            ),
                            rx.heading(
                                "AI 챗봇",
                                size="6",
                                background="linear-gradient(135deg, #667eea 0%, #764ba2 100%)",
                                background_clip="text",
                                font_weight="700",
                            ),
                            spacing="3",
                            align="center",
                        ),
                        rx.hstack(
                            # 연결 상태 인디케이터 (세션 활성화 여부)
                            rx.badge(
                                rx.hstack(
                                    rx.box(
                                        width="8px",
                                        height="8px",
                                        border_radius="50%",
                                        background=rx.cond(
                                            State.is_connected,
                                            "#10b981",  # 초록색 (세션 활성)
                                            "#94a3b8",  # 회색 (세션 없음)
                                        ),
                                    ),
                                    rx.text(
                                        State.connection_status,
                                        font_size="12px",
                                    ),
                                    spacing="2",
                                    align="center",
                                ),
                                variant="soft",
                                color_scheme=rx.cond(
                                    State.is_connected,
                                    "green",
                                    "gray",
                                ),
                            ),
                            rx.button(
                                rx.icon("trash-2", size=18),
                                on_click=State.clear_messages,
                                variant="ghost",
                                color_scheme="gray",
                                size="2",
                            ),
                            rx.color_mode.button(
                                variant="ghost",
                                color_scheme="gray",
                                size="2",
                            ),
                            spacing="2",
                        ),
                        justify="between",
                        align="center",
                        width="100%",
                    ),
                    padding="20px",
                    border_bottom="1px solid",
                    border_color=rx.color("gray", 4),
                    background=rx.color("gray", 1),
                    width="100%",
                ),
                # 메시지 히스토리 영역
                rx.box(
                    rx.cond(
                        State.messages.length() == 0,  # type: ignore
                        rx.center(
                            rx.vstack(
                                rx.icon(
                                    "message-circle",
                                    size=48,
                                    color=rx.color("gray", 8),
                                ),
                                rx.text(
                                    "대화를 시작해보세요",
                                    font_size="18px",
                                    font_weight="600",
                                    color=rx.color("gray", 11),
                                ),
                                rx.text(
                                    "메시지를 입력하면 AI가 응답합니다",
                                    font_size="14px",
                                    color=rx.color("gray", 9),
                                ),
                                spacing="3",
                                align="center",
                            ),
                            width="100%",
                            height="100%",
                        ),
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
                        ),
                    ),
                    flex="1",
                    overflow_y="auto",
                    padding="20px",
                    background=rx.color("gray", 2),
                    width="100%",
                ),
                # 입력 영역
                rx.box(
                    rx.vstack(
                        recommended_questions_section(),
                        rx.hstack(
                            rx.text_area(
                                placeholder="메시지를 입력하세요... (전송 버튼을 클릭하여 전송)",
                                value=State.current_message,
                                on_change=State.set_current_message,
                                variant="soft",
                                name="message_input",
                                resize="none",
                                width="100%",
                                min_height="100px",
                                style={
                                    "font_size": "16px",
                                    "padding": "12px",
                                },
                            ),
                            rx.button(
                                rx.icon("send", size=24),
                                on_click=State.send_message,
                                disabled=State.is_loading,
                                variant="solid",
                                style={
                                    "background": "linear-gradient(135deg, #667eea 0%, #764ba2 100%)",
                                    "cursor": "pointer",
                                    "min_height": "100px",
                                    "min_width": "80px",
                                    "border_radius": "12px",
                                    "box_shadow": "0 4px 12px rgba(102, 126, 234, 0.3)",
                                    "_hover": {
                                        "transform": "translateY(-2px)",
                                        "box_shadow": "0 6px 16px rgba(102, 126, 234, 0.4)",
                                    },
                                    "_active": {
                                        "transform": "translateY(0)",
                                    },
                                },
                            ),
                            spacing="3",
                            width="100%",
                            align="end",
                        ),
                        spacing="3",
                        width="100%",
                    ),
                    padding="24px",
                    border_top="1px solid",
                    border_color=rx.color("gray", 4),
                    background=rx.color("gray", 1),
                    width="100%",
                ),
                spacing="0",
                width="100%",
                max_width="900px",
                height="100vh",
                box_shadow="0 0 60px rgba(0, 0, 0, 0.08)",
            ),
            width="100%",
            height="100vh",
        ),
        width="100%",
        min_height="100vh",
        background=rx.color("gray", 3),
    )


app = rx.App(
    stylesheets=[
        "https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap",
    ],
    style={
        "font_family": "Inter, sans-serif",
    },
)

app.add_page(index)
