# Example Agent

예제 AI 에이전트 패키지

## 설치

루트 디렉토리에서:
```bash
uv sync
```

## 실행

```bash
uv run --package example-agent python -m example_agent
```

## 사용법

```python
from example_agent import ExampleAgent

agent = ExampleAgent(name="MyAgent")
result = agent.run("sample task")
print(result)
```

## 구조

```
example-agent/
├── example_agent/
│   ├── __init__.py
│   ├── __main__.py
│   └── agent.py
├── pyproject.toml
└── README.md
```
