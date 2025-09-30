# AI Agent Platform

모노레포 기반 AI Agent 시스템 플랫폼

## 구조

```
ai-agent-platform/
├── agents/              # AI 에이전트 패키지들
│   └── [에이전트별 패키지]
├── mcp-servers/         # MCP 서버 패키지들
│   └── [서버별 패키지]
├── pyproject.toml       # 루트 워크스페이스 설정
└── README.md
```

## 패키지 관리

이 프로젝트는 [uv](https://github.com/astral-sh/uv)를 사용하여 모노레포를 관리합니다.

### 새 에이전트 추가

```bash
# agents 폴더에 새 패키지 생성
cd agents
mkdir my-agent
cd my-agent

# pyproject.toml 생성 (아래 템플릿 참조)
```

### 새 MCP 서버 추가

```bash
# mcp-servers 폴더에 새 패키지 생성
cd mcp-servers
mkdir my-server
cd my-server

# pyproject.toml 생성 (아래 템플릿 참조)
```

### 의존성 설치

```bash
# 루트에서 모든 워크스페이스 패키지 설치
uv sync
```

### 특정 패키지 실행

```bash
# 특정 에이전트 실행
uv run --package agent-name python -m agent_name

# 특정 MCP 서버 실행
uv run --package server-name python -m server_name
```

## 패키지 템플릿

### Agent 패키지 템플릿

```toml
[project]
name = "agent-name"
version = "0.1.0"
description = "Description of the agent"
requires-python = ">=3.12"
dependencies = [
    # 필요한 의존성 추가
]

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"
```

### MCP Server 패키지 템플릿

```toml
[project]
name = "mcp-server-name"
version = "0.1.0"
description = "Description of the MCP server"
requires-python = ">=3.12"
dependencies = [
    # 필요한 의존성 추가
]

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"
```

## 개발 가이드

### 워크스페이스 패키지 간 의존성

다른 워크스페이스 패키지를 의존성으로 추가하려면:

```toml
[project]
dependencies = [
    "other-package"
]

[tool.uv.sources]
other-package = { workspace = true }
```

### 공통 의존성

여러 패키지에서 사용하는 공통 의존성은 각 패키지의 `pyproject.toml`에 개별적으로 명시하거나, 
공통 라이브러리 패키지를 만들어 관리할 수 있습니다.

## 라이선스

MIT
