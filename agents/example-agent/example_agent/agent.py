"""Example Agent implementation"""

from agent_common import get_logger

logger = get_logger(__name__)


class ExampleAgent:
    """예제 AI 에이전트"""

    def __init__(self, name: str = "ExampleAgent") -> None:
        """에이전트 초기화"""
        self.name = name

    def run(self, task: str) -> str:
        """에이전트 실행"""
        message = f"{self.name} is processing task: {task}"
        logger.info(message)
        return message


def main() -> None:
    """메인 함수"""
    agent = ExampleAgent()
    result = agent.run("example task")
    print(result)


if __name__ == "__main__":
    main()
