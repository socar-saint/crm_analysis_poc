# Docker Compose 가이드

이 디렉토리에는 AI Agent Platform의 Docker 설정 파일들이 포함되어 있습니다.

## 서비스 구성

### VOC (Voice of Customer) 스택
- `mcp-server`: MCP 서버 (포트 9000)
- `audio-processing`: 오디오 처리 에이전트 (포트 10001, 화자 분리·STT·마스킹 포함)
- `orchestrator`: 오케스트레이션 에이전트 (포트 10000)
- `ui-for-simple-test`: 테스트용 웹 UI (포트 3000, 8000)

## 실행 방법

### 1. 환경 변수 설정

프로젝트 루트에 `.env` 파일을 생성하고 필요한 환경 변수를 설정합니다:

```bash
# Azure OpenAI 설정
AZURE_OPENAI_API_KEY=your_api_key
AZURE_OPENAI_ENDPOINT=your_endpoint
AZURE_OPENAI_DEPLOYMENT=your_deployment
AZURE_OPENAI_API_VERSION=2024-12-01-preview

# AWS 설정 (선택사항)
AWS_ACCESS_KEY_ID=your_access_key
AWS_SECRET_ACCESS_KEY=your_secret_key
AWS_REGION=us-east-1
```

### 2. 전체 스택 실행

```bash
cd docker
docker-compose -f voc/docker-compose.yml up -d
```

### 3. 특정 서비스만 실행

```bash
# UI만 실행 (orchestrator에 의존)
docker-compose -f voc/docker-compose.yml up -d ui-for-simple-test

# VOC 스택만 실행 (UI 제외)
docker-compose -f voc/docker-compose.yml up -d mcp-server audio-processing orchestrator
```

### 4. 로그 확인

```bash
# 모든 서비스 로그
docker-compose -f voc/docker-compose.yml logs -f

# 특정 서비스 로그
docker-compose -f voc/docker-compose.yml logs -f ui-for-simple-test
```

### 5. 중지 및 삭제

```bash
# 중지
docker-compose -f voc/docker-compose.yml stop

# 중지 및 컨테이너 삭제
docker-compose -f voc/docker-compose.yml down

# 중지, 컨테이너 및 볼륨 삭제
docker-compose -f voc/docker-compose.yml down -v
```

## 접속 정보

서비스가 실행되면 다음 주소로 접속할 수 있습니다:

- **UI for Simple Test**: http://localhost:3000
- **Orchestrator**: http://localhost:10000
- **Audio Processing**: http://localhost:10001
- **MCP Server**: http://localhost:9000

## 개발 모드

개발 중에는 로컬에서 서비스를 실행하고, UI만 Docker로 실행할 수 있습니다:

```bash
# 로컬에서 VOC 스택 실행
cd agents/voc-agent
uv run python -m voc_agent.orchestrator.__main__

# Docker로 UI 실행 (orchestrator_host를 host.docker.internal로 설정)
docker-compose -f voc/docker-compose.yml up -d ui-for-simple-test
```

## 트러블슈팅

### 포트 충돌
다른 서비스가 이미 포트를 사용 중인 경우, `voc/docker-compose.yml`에서 포트 매핑을 변경할 수 있습니다.

### 네트워크 연결 문제
서비스 간 통신이 안 되는 경우, 모든 서비스가 같은 Docker 네트워크(`voc-net`)에 있는지 확인합니다:

```bash
docker network inspect voc-net
```

### 이미지 재빌드
코드를 변경한 후에는 이미지를 다시 빌드해야 합니다:

```bash
docker-compose -f voc/docker-compose.yml build
docker-compose -f voc/docker-compose.yml up -d
```

특정 서비스만 재빌드:

```bash
docker-compose -f voc/docker-compose.yml build ui-for-simple-test
docker-compose -f voc/docker-compose.yml up -d ui-for-simple-test
```
