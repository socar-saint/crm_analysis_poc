"""Agent Client."""

import argparse
import asyncio
import inspect
import traceback
from uuid import uuid4

import httpx
from a2a.client import A2ACardResolver, ClientConfig, ClientFactory
from a2a.types import Message, Role, TextPart

from .text_utils import extract_response_models_from_task, get_human_text_from_response

AGENT_URL = "http://localhost:10000"


async def run_single_turn_test(message: str) -> None:
    """Runs a single-turn non-streaming test."""

    print(f"--- Connecting to agent at {AGENT_URL}... ---")
    try:
        async with httpx.AsyncClient(timeout=httpx.Timeout(1200)) as httpx_client:
            card_resolver = A2ACardResolver(httpx_client=httpx_client, base_url=AGENT_URL)
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

            # 스트리밍/논-스트리밍 모두 호환
            result = client.send_message(request)
            if inspect.isasyncgen(result):
                # 스트리밍이면 마지막 이벤트(보통 최종 Task)를 결과로
                last_event = None
                async for ev in result:
                    last_event = ev
                task_or_tuple = last_event
            else:
                task_or_tuple = await result

            # (Task, None) 같은 튜플이면 첫 요소 사용
            task = task_or_tuple[0] if isinstance(task_or_tuple, tuple | list) else task_or_tuple
            print("--- Response successful ---")

            # response만 추출하여 model_dump()로 출력
            responses = extract_response_models_from_task(task)
            if not responses:
                print("(no response payloads found)")
                return

            # 마지막 응답만 선택
            last_resp = responses[-1].model_dump()

            human_text = get_human_text_from_response(last_resp).strip()
            if not human_text:
                print("(no human-readable text could be extracted)")
                return

            print("\n==== LAST TASK TEXT (human-readable) ====\n")
            print(human_text)
            print("\n=========================================\n")

    except Exception as e:
        traceback.print_exc()
        print(f"--- An error occurred: {e} ---")
        print("Ensure the agent server is running.")


if __name__ == "__main__":
    p = argparse.ArgumentParser(description="Agent Client (Google ADK Tool-Calling)")
    p.add_argument("command", nargs="+", help="자연어 명령. 예) '이 파일 처리해줘: /path/상담내역1.opus'")
    p.add_argument("--speakers", default="상담사,고객")
    args = p.parse_args()

    cmd = "".join(args.command)
    speakers = args.speakers
    if speakers:
        cmd += f"\n(스피커 라벨: {speakers})"

    asyncio.run(run_single_turn_test(message=cmd))
