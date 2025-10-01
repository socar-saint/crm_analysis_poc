# voc-agent

VOC 프로젝트에서 사용하는 오케스트레이션 에이전트와 다이얼라이제이션 워커를 하나의 패키지로 묶었습니다.

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
    └── diarization/
        ├── __init__.py
        └── diarization_agent.py
```

> 공통 A2A 모델은 `packages/common/agent_common/a2a.py`에 정의되어 있습니다.

## 실행

```bash
uv run python -m agents.voc-agent.voc_agent.diarization

# another terminal
uv run adk web agents/voc-agent
```
