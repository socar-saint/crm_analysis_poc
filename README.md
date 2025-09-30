# AI Agent Platform

모노레포 기반 AI Agent 시스템 플랫폼

## 구조

```
ai-agent-platform/
├── agents/              # AI 에이전트 패키지들
│   └── [에이전트별 패키지]
├── packages/            # 공통 유틸리티 및 재사용 가능 패키지
│   └── [공통 패키지]
├── mcp-servers/         # MCP 서버 패키지들
│   └── [서버별 패키지]
├── pyproject.toml       # 루트 워크스페이스 설정
└── README.md
```


### 의존성 설치

```bash
# 루트에서 모든 워크스페이스 패키지 설치
uv sync --package agent-name
```

### 특정 패키지 실행

```bash
# 특정 에이전트 실행
uv run --package agent-name python -m agent_name

# 특정 MCP 서버 실행
uv run --package server-name python -m server_name
```
