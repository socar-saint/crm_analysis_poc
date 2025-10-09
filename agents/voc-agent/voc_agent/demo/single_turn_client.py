"""Single-turn demo client for the VOC agent."""

import argparse
import asyncio
import inspect
import traceback
from typing import Any
from uuid import uuid4

import httpx
from a2a.client import A2ACardResolver, ClientConfig, ClientFactory
from a2a.types import Message, Role, TextPart

from ..settings import settings
from .text_utils import extract_response_models_from_task, get_human_text_from_response

DEFAULT_AGENT_URL = settings.orchestrator_base_url


async def _execute_single_turn_request(message: str, resolved_url: str) -> Any:
    """Send a single message and return the resulting task payload."""

    async with httpx.AsyncClient(timeout=httpx.Timeout(1200)) as httpx_client:
        card_resolver = A2ACardResolver(httpx_client=httpx_client, base_url=resolved_url)
        card = await card_resolver.get_agent_card()
        client_config = ClientConfig(httpx_client=httpx_client, streaming=False)
        factory = ClientFactory(config=client_config)
        client = factory.create(card=card)

        print("--- Connection successful ---")

        request = Message(
            message_id=str(uuid4()),
            role=Role.user,
            parts=[TextPart(text=message)],
        )

        result = client.send_message(request)
        task = await _resolve_task_from_result(result)

        print("--- Response successful ---")
        return task


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
    """Return the human-readable text from the final task response."""

    responses = extract_response_models_from_task(task)
    if responses:
        last_resp = responses[-1].model_dump()
        human_text = get_human_text_from_response(last_resp).strip()
        if human_text:
            return human_text

    return _latest_agent_text(task)


def _latest_agent_text(task: Any) -> str:
    """Fallback to the agent's latest text message when no response payload exists."""

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


async def run_single_turn_test(message: str, agent_url: str | None = None) -> None:
    """Runs a single-turn non-streaming test against the orchestrator."""

    resolved_url = agent_url or DEFAULT_AGENT_URL
    print(f"--- Connecting to agent at {resolved_url}... ---")
    try:
        task = await _execute_single_turn_request(message, resolved_url)
    except Exception as e:  # pragma: no cover - surfaced to user via print
        traceback.print_exc()
        print(f"--- An error occurred: {e} ---")
        print("Ensure the agent server is running.")
        return

    human_text = _extract_human_text_from_task(task)
    if not human_text:
        print("(no response payloads found)")
        return

    print("\n==== LAST TASK TEXT (human-readable) ====\n")
    print(human_text)
    print("\n=========================================\n")


def main() -> None:
    """Main function."""
    parser = argparse.ArgumentParser(description="Agent Client (Google ADK Tool-Calling)")
    parser.add_argument(
        "command",
        nargs="+",
        help="자연어 명령. 예) '이 파일 처리해줘: /path/상담내역1.opus'",
    )
    parser.add_argument("--speakers", default="상담사,고객")
    parser.add_argument(
        "--agent-url",
        default=None,
        help=f"Override orchestrator base URL (default: {DEFAULT_AGENT_URL})",
    )
    args = parser.parse_args()

    cmd = "".join(args.command)
    speakers = args.speakers
    if speakers:
        cmd += f"\n(스피커 라벨: {speakers})"

    asyncio.run(run_single_turn_test(message=cmd, agent_url=args.agent_url))


if __name__ == "__main__":
    main()
