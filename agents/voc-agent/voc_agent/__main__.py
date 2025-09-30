"""VOC 에이전트 데모 엔트리포인트."""

from . import VocDiarizationAgent, VocOrchestrationAgent


def main() -> None:
    """VOC 에이전트 데모 엔트리포인트"""
    orchestrator = VocOrchestrationAgent(diarization_worker=VocDiarizationAgent())
    result = orchestrator.handle_request("customer_call.wav")
    print(result.summary)


if __name__ == "__main__":
    main()
