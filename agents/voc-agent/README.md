# voc-agent

## 구조

```
voc-agent/
├── pyproject.toml
└── voc_agent/
    ├── __init__.py
    ├── __main__.py
    ├── orchestrator/
    │   ├── __init__.py
    │   └── orchestration_agent.py
    └── audio_processing/
        ├── audio_processing_agent.py
        ├── audio_processing_server.py
        └── __init__.py
```

> 공통 A2A 모델은 `packages/common/agent_common/a2a.py`에 정의되어 있습니다.

## 실행

```bash
uv run python -m agents.voc-agent.voc_agent.audio_processing

# another terminal
uv run adk web agents/voc-agent
```
