# 설치 가이드

> **CRM 캠페인 분석 시스템 완전 설정 가이드**

*by saintwo*

---

## 🎯 빠른 시작

### 사전 요구사항

- **Python 3.11+** (권장: Python 3.11.7)
- **UV 패키지 매니저** (현대적인 Python 패키지 매니저)
- **Azure OpenAI API 액세스** (GPT-4 또는 동등한 것)
- **Google ADK** (Agent Development Kit)
- **Git** (버전 관리용)

### 시스템 요구사항

- **RAM**: 최소 8GB, 권장 16GB+
- **저장공간**: 2GB 여유 공간
- **OS**: macOS, Linux, 또는 WSL2가 있는 Windows
- **네트워크**: API 호출을 위한 안정적인 인터넷 연결

---

## 📦 설치 단계

### 1. 환경 설정

```bash
# UV 패키지 매니저 설치 (이미 설치되지 않은 경우)
curl -LsSf https://astral.sh/uv/install.sh | sh

# 설치 확인
uv --version
```

### 2. 프로젝트 설정

```bash
# 프로젝트 디렉토리로 이동
cd crm-analysis-agent

# 가상 환경 생성 및 의존성 설치
uv sync

# 환경 활성화
source .venv/bin/activate  # macOS/Linux에서
# 또는
.venv\Scripts\activate     # Windows에서
```

### 3. 구성

#### Azure OpenAI 설정

1. **API 자격 증명 받기**
   - Azure OpenAI 서비스에 가입
   - 배포 생성 (권장: GPT-4)
   - API 키와 엔드포인트 기록

2. **환경 변수 구성**
   ```bash
   # .env 파일 생성
   touch .env
   
   # 자격 증명 추가
   echo "AZURE_OPENAI_API_KEY=your-api-key-here" >> .env
   echo "AZURE_OPENAI_ENDPOINT=https://your-resource.openai.azure.com/" >> .env
   echo "AZURE_OPENAI_API_VERSION=2024-02-15-preview" >> .env
   echo "AZURE_OPENAI_DEPLOYMENT_NAME=your-deployment-name" >> .env
   ```

3. **구성 파일 업데이트**
   ```python
   # config/settings.py 편집
   AZURE_OPENAI_API_KEY = os.getenv("AZURE_OPENAI_API_KEY")
   AZURE_OPENAI_ENDPOINT = os.getenv("AZURE_OPENAI_ENDPOINT")
   AZURE_OPENAI_API_VERSION = os.getenv("AZURE_OPENAI_API_VERSION", "2024-02-15-preview")
   AZURE_OPENAI_DEPLOYMENT_NAME = os.getenv("AZURE_OPENAI_DEPLOYMENT_NAME")
   ```

### 4. Google ADK 설정

```bash
# Google ADK 설치
pip install google-adk

# 설치 확인
python -c "from google.adk.agents import Agent; print('ADK가 성공적으로 설치되었습니다')"
```

---

## 🧪 검증

### 설치 테스트

```bash
# 기본 시스템 확인 실행
uv run python -c "
import sys
print(f'Python 버전: {sys.version}')
try:
    from google.adk.agents import Agent
    print('✅ Google ADK: OK')
except ImportError as e:
    print(f'❌ Google ADK: {e}')

try:
    import litellm
    print('✅ LiteLLM: OK')
except ImportError as e:
    print(f'❌ LiteLLM: {e}')

try:
    import pandas as pd
    print('✅ Pandas: OK')
except ImportError as e:
    print(f'❌ Pandas: {e}')
"
```

### API 연결 테스트

```bash
# Azure OpenAI 연결 테스트
uv run python -c "
from config.settings import azure_llm
try:
    response = azure_llm.completion(
        model='gpt-4.1-for-sales-tf',
        messages=[{'role': 'user', 'content': '안녕하세요, 테스트 메시지입니다'}]
    )
    print('✅ Azure OpenAI API: 성공적으로 연결되었습니다')
except Exception as e:
    print(f'❌ Azure OpenAI API: {e}')
"
```

---

## 🚀 첫 실행

### 샘플 데이터 준비

```bash
# data/raw/에 샘플 CSV 데이터가 있는지 확인
ls data/raw/
# 표시되어야 함: 251014_claned_Sales_TF_분석.csv 또는 유사한 파일
```

### 분석 실행

```bash
# 메인 분석 파이프라인 실행
uv run main.py

# 예상 출력:
# - 데이터 검증 메시지
# - 에이전트 실행 진행률
# - 보고서 생성 상태
# - 최종 HTML 보고서 경로
```

### 출력 확인

```bash
# 생성된 보고서 확인
ls outputs/reports/$(date +%Y%m%d)/
# HTML 보고서 및 분석 파일이 표시되어야 함
```

---

## 🔧 고급 구성

### 성능 튜닝

#### 메모리 최적화

```python
# config/settings.py에서
MAX_SAMPLE_SIZE = 1000  # LLM 분석 샘플 크기 제한
CHUNK_SIZE = 100       # 청크 단위로 데이터 처리
CACHE_RESULTS = True   # 결과 캐싱 활성화
```

#### 병렬 처리

```python
# 동시 에이전트 실행 활성화
ENABLE_PARALLEL_EXECUTION = True
MAX_CONCURRENT_AGENTS = 3
```

### 사용자 정의 분석 매개변수

```python
# core/analysis/analysis_tools.py에서
LIFT_SIGNIFICANCE_THRESHOLD = 0.05  # 통계적 유의성 수준
MIN_SAMPLE_SIZE = 30                # 분석을 위한 최소 샘플 크기
CONFIDENCE_INTERVAL = 0.95          # 지표에 대한 신뢰 구간
```

---

## 🐛 문제 해결

### 일반적인 문제

#### 1. 가져오기 오류

```bash
# 오류: ModuleNotFoundError: No module named 'google'
# 해결책: Google ADK 설치
pip install google-adk

# 오류: ModuleNotFoundError: No module named 'litellm'
# 해결책: LiteLLM 설치
pip install litellm
```

#### 2. API 연결 문제

```bash
# 오류: Azure OpenAI API 연결 실패
# 해결책:
# 1. API 키와 엔드포인트 확인
# 2. 배포 이름 확인
# 3. 네트워크 연결 확인
# 4. Azure 서비스 상태 확인
```

#### 3. 메모리 문제

```bash
# 오류: 분석 중 메모리 부족
# 해결책:
# 1. 설정에서 샘플 크기 줄이기
# 2. 더 작은 청크로 데이터 처리
# 3. 시스템 RAM 증가
# 4. 대규모 데이터셋에 데이터 샘플링 사용
```

#### 4. 데이터 형식 문제

```bash
# 오류: CSV 파싱 실패
# 해결책:
# 1. CSV 인코딩 확인 (UTF-8이어야 함)
# 2. 열 이름이 예상 스키마와 일치하는지 확인
# 3. 잘못된 행 확인
# 4. 데이터 유형 검증
```

### 성능 문제

#### 느린 실행

```bash
# 속도 최적화:
# 1. 병렬 처리 활성화
# 2. 더 작은 샘플 크기 사용
# 3. 중간 결과 캐싱
# 4. LLM 프롬프트 최적화
```

#### 높은 메모리 사용량

```bash
# 메모리 최적화:
# 1. 청크 단위로 데이터 처리
# 2. 중간 변수 정리
# 3. 데이터 샘플링 사용
# 4. 메모리 사용량 모니터링
```

---

## 📊 시스템 모니터링

### 상태 확인

```bash
# 상태 확인 스크립트 생성
cat > health_check.py << 'EOF'
#!/usr/bin/env python3
import sys
import importlib

def check_dependency(module_name, package_name=None):
    try:
        importlib.import_module(module_name)
        print(f"✅ {package_name or module_name}: OK")
        return True
    except ImportError:
        print(f"❌ {package_name or module_name}: 누락됨")
        return False

def main():
    dependencies = [
        ('google.adk.agents', 'Google ADK'),
        ('litellm', 'LiteLLM'),
        ('pandas', 'Pandas'),
        ('numpy', 'NumPy'),
        ('matplotlib', 'Matplotlib'),
    ]
    
    all_ok = True
    for module, name in dependencies:
        if not check_dependency(module, name):
            all_ok = False
    
    if all_ok:
        print("\n🎉 모든 의존성이 올바르게 설치되었습니다!")
        sys.exit(0)
    else:
        print("\n❌ 일부 의존성이 누락되었습니다. 설치해주세요.")
        sys.exit(1)

if __name__ == "__main__":
    main()
EOF

# 상태 확인 실행
uv run python health_check.py
```

### 성능 모니터링

```bash
# 실행 중 시스템 리소스 모니터링
# macOS/Linux에서:
top -pid $(pgrep -f "main.py")

# 메모리 사용량 모니터링
ps aux | grep "main.py"
```

---

## 🔄 업데이트 및 유지보수

### 의존성 업데이트

```bash
# 모든 의존성 업데이트
uv sync --upgrade

# 특정 패키지 업데이트
uv add package-name@latest
```

### 백업 및 복구

```bash
# 업데이트 전 백업 생성
cp -r crm-analysis-agent crm-analysis-agent_$(date +%Y%m%d)

# 백업에서 복구
cp -r crm-analysis-agent_20251016 crm-analysis-agent
```

---

## 📞 지원

### 도움 받기

1. **로그 확인**: 오류 세부사항에 대한 실행 로그 검토
2. **구성 확인**: 모든 설정이 올바른지 확인
3. **구성 요소 테스트**: 문제를 격리하기 위해 개별 구성 요소 실행
4. **문서**: 자세한 사용법은 README.md 참조

### 일반적인 명령어

```bash
# 최근 로그 보기
tail -f logs/analysis.log

# 시스템 상태 확인
uv run python health_check.py

# 상세 출력으로 실행
uv run main.py --verbose

# 특정 구성 요소 테스트
uv run python -c "from core.analysis.analysis_tools import *; print('분석 도구가 로드되었습니다')"
```

---

*설치 가이드 by saintwo - 마지막 업데이트: 2025년 10월*