# Example MCP Server

예제 MCP 서버 패키지

## 설치

루트 디렉토리에서:
```bash
uv sync
```

## 실행

```bash
uv run --package example-server python -m example_server
```

## 사용법

```python
from example_server import ExampleServer

server = ExampleServer(host="localhost", port=8000)
server.start()
```

## 구조

```
example-server/
├── example_server/
│   ├── __init__.py
│   ├── __main__.py
│   └── server.py
├── pyproject.toml
└── README.md
```
