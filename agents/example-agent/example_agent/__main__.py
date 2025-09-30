"""Example agent 데모 엔트리포인트."""

from .orchestrator import ExampleOrchestratorAgent


def main() -> None:
    """Example agent 데모 엔트리포인트"""
    orchestrator = ExampleOrchestratorAgent()
    response = orchestrator.run("샘플 응답 생성")
    print(response.summary)


if __name__ == "__main__":
    main()
