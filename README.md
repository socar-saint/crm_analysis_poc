# AI Agent Platform

uv 기반 모노레포 AI Agent 시스템 플랫폼

## 구조

```
ai-agent-platform/
├── agents/                    # AI 에이전트 패키지들
│   ├── voc-agent/            # 음성 처리 및 상담 분석 에이전트
│   └── example-agent/        # 예제 에이전트
├── mcp-servers/              # MCP 서버 패키지들
│   ├── voc-server/           # 음성 처리 MCP 서버
│   └── example-server/       # 예제 MCP 서버
├── packages/                 # 공통 유틸리티 및 재사용 가능 패키지
│   ├── common/               # 공통 라이브러리 (ai-common)
│   └── ui-for-simple-test/   # 테스트용 UI 패키지
├── docker/                   # Docker 설정 파일들
├── pyproject.toml            # 루트 워크스페이스 설정
└── README.md
```

## 설치 및 실행

### 모든 패키지 설치

```bash
# 모든 워크스페이스 패키지를 한번에 설치
uv sync

# 개발 의존성도 함께 설치
uv sync --dev
```

### 특정 패키지만 설치

```bash
# 특정 에이전트만 설치
uv sync --package voc-agent

# 특정 MCP 서버만 설치
uv sync --package voc-server

# 특정 공통 패키지만 설치
uv sync --package ai-common
```

### 패키지 실행

```bash
# VOC 에이전트 실행
uv run --package voc-agent python -m voc_agent

# VOC MCP 서버 실행
uv run --package voc-server python -m voc_server

# 특정 모듈 실행
uv run --package voc-agent python -m voc_agent.audio_processing
uv run --package voc-agent python -m voc_agent.consultation_analysis
uv run --package voc-agent python -m voc_agent.orchestrator
```

## 개발 환경

### 코드 품질 도구

```bash
# 코드 포맷팅
uv run black .

# 린팅
uv run ruff check .

# 타입 체킹
uv run mypy .

# 테스트 실행
uv run pytest
```

### 의존성 관리

- **uv**: 패키지 관리 및 가상환경 관리
- **모노레포**: 모든 패키지가 하나의 워크스페이스에서 관리됨
- **워크스페이스 멤버**: `pyproject.toml`의 `[tool.uv.workspace]` 섹션에서 정의
- **로컬 의존성**: `[tool.uv.sources]`에서 워크스페이스 패키지들을 명시

## 패키지별 상세 정보

### Agents
- **voc-agent**: 음성 처리, 상담 분석, 오케스트레이션 기능을 제공하는 AI 에이전트

### MCP Servers
- **voc-server**: 음성 파일 처리, 전사, 화자 분리 등의 MCP 서버

### Common Packages
- **ai-common**: 플랫폼 전반에서 사용되는 공통 유틸리티 및 헬퍼 함수들
