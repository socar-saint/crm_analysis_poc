"""Example Agent implementation"""


class ExampleAgent:
    """예제 AI 에이전트"""

    def __init__(self, name: str = "ExampleAgent"):
        self.name = name

    def run(self, task: str) -> str:
        """에이전트 실행"""
        return f"{self.name} is processing task: {task}"


def main():
    """메인 함수"""
    agent = ExampleAgent()
    result = agent.run("example task")
    print(result)


if __name__ == "__main__":
    main()
