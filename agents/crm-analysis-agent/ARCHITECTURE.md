# 시스템 아키텍처

> **CRM 캠페인 분석 시스템 기술 심화 분석**

*by saintwo*

---

## 🏗️ 고수준 아키텍처

### 시스템 개요

CRM 캠페인 분석 시스템은 통계적 분석과 고급 LLM 기반 인사이트를 결합한 **멀티 에이전트 아키텍처**를 기반으로 구축되었습니다. 시스템은 전문 AI 에이전트의 정교한 파이프라인을 통해 CRM 캠페인 데이터를 처리하며, 각각은 분석의 다른 측면을 담당합니다.

```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   입력 데이터    │───▶│  에이전트 파이프라인  │───▶│  HTML 보고서     │
│   (CSV 파일)     │    │                  │    │                 │
└─────────────────┘    └──────────────────┘    └─────────────────┘
```

### 핵심 설계 원칙

- **모듈성**: 각 에이전트는 단일 책임을 가짐
- **확장성**: 에이전트 병렬화를 통한 수평적 확장
- **신뢰성**: 강력한 오류 처리 및 복구 메커니즘
- **확장성**: 새로운 에이전트 및 분석 유형의 쉬운 추가
- **성능**: 대규모 데이터 처리에 최적화

---

## 🤖 에이전트 아키텍처

### 에이전트 파이프라인 흐름

```
데이터 이해 → 통계적 분석 → LLM 분석 → 종합 분석 → 보고서 생성
```

### 에이전트 책임

#### 1. 데이터 이해 에이전트
- **목적**: 입력 데이터 구조 검증 및 이해
- **입력**: 원시 CSV 파일
- **출력**: 검증된 데이터 스키마 및 기본 통계
- **도구**: `validate_csv_terms_simple`, `get_domain_glossary`

#### 2. 통계적 분석 에이전트
- **목적**: 캠페인 성과의 통계적 분석 수행
- **입력**: 검증된 캠페인 데이터
- **출력**: 전환율, 리프트 계산, 퍼널 지표
- **도구**: `analyze_conversion_performance_tool`, `analyze_funnel_performance_tool`

#### 3. LLM 분석 에이전트
- **목적**: 캠페인 메시지 및 콘텐츠의 의미론적 분석
- **입력**: 메시지 콘텐츠 및 성과 데이터
- **출력**: 콘텐츠 효과성 인사이트 및 권장사항
- **도구**: `prepare_funnel_message_analysis_data`, `structure_llm_analysis_for_html`

#### 4. 종합 분석 에이전트
- **목적**: 이전 모든 에이전트의 인사이트 통합
- **입력**: 모든 분석 에이전트의 결과
- **출력**: 통합된 인사이트 및 전략적 권장사항
- **도구**: `generate_comprehensive_report`, `create_actionable_recommendations`

#### 5. 보고서 생성 에이전트
- **목적**: 경영진 보고서 및 시각화 생성
- **입력**: 모든 분석 결과
- **출력**: HTML 보고서, 차트, 데이터 내보내기
- **도구**: `create_segment_conversion_table`, `generate_text_analysis_report`

---

## 🔧 기술 스택

### 핵심 기술

#### AI/ML 프레임워크
- **Google ADK**: 에이전트 프레임워크 및 오케스트레이션
- **LiteLLM**: 멀티 제공업체 LLM 추상화 계층
- **Azure OpenAI**: 기본 LLM 제공업체 (GPT-4)

#### 데이터 처리
- **Pandas**: 데이터 조작 및 분석
- **NumPy**: 수치 계산
- **SciPy**: 통계적 분석
- **Scikit-learn**: 머신러닝 유틸리티

#### 시각화 및 보고서
- **Matplotlib/Seaborn**: 통계적 시각화
- **Plotly**: 대화형 차트
- **Jinja2**: HTML 템플릿 엔진
- **BeautifulSoup**: HTML 처리

#### 인프라
- **UV**: 현대적인 Python 패키지 관리
- **Asyncio**: 비동기 실행
- **Pydantic**: 데이터 검증 및 직렬화

### 아키텍처 패턴

#### 1. 에이전트 패턴
```python
class Agent:
    def __init__(self, name: str, tools: List[Tool], prompt: str):
        self.name = name
        self.tools = tools
        self.prompt = prompt
    
    async def execute(self, context: Context) -> Result:
        # 에이전트 실행 로직
        pass
```

#### 2. 컨텍스트 전달 패턴
```python
class Context:
    def __init__(self):
        self.data = {}
        self.results = {}
    
    def add_result(self, agent_name: str, result: Any):
        self.results[agent_name] = result
```

#### 3. 도구 패턴
```python
class Tool:
    def __init__(self, name: str, function: Callable):
        self.name = name
        self.function = function
    
    async def execute(self, *args, **kwargs):
        return await self.function(*args, **kwargs)
```

---

## 📊 데이터 흐름 아키텍처

### 입력 데이터 처리

```
CSV 파일 → 데이터 검증 → 스키마 매핑 → 통계적 분석 → LLM 분석 → 보고서 생성
```

### 데이터 변환 파이프라인

#### 1. 데이터 수집
- **형식**: 캠페인 데이터가 포함된 CSV 파일
- **검증**: 스키마 검증 및 데이터 품질 확인
- **정리**: 누락된 값 및 데이터 불일치 처리

#### 2. 통계적 처리
- **전환 분석**: 실험 vs 대조 그룹 성과 계산
- **리프트 계산**: 통계적 유의성 테스트
- **퍼널 분석**: 단계별 전환 최적화

#### 3. LLM 처리
- **콘텐츠 분석**: 캠페인 메시지의 의미론적 분석
- **효과성 점수**: LLM 기반 성과 평가
- **권장사항 생성**: AI 기반 최적화 제안

#### 4. 보고서 생성
- **데이터 집계**: 모든 분석 결과 결합
- **시각화**: 차트 및 그래프 생성
- **HTML 렌더링**: 경영진 보고서 생성

---

## 🔄 실행 흐름

### 동기 실행
```python
async def run_analysis_pipeline(csv_file: str):
    context = Context()
    
    # 순차적 에이전트 실행
    for agent in agents:
        result = await agent.execute(context)
        context.add_result(agent.name, result)
    
    return context
```

### 병렬 실행
```python
async def run_parallel_analysis(csv_file: str):
    context = Context()
    
    # 독립적인 작업에 대한 병렬 에이전트 실행
    tasks = [agent.execute(context) for agent in independent_agents]
    results = await asyncio.gather(*tasks)
    
    return context
```

### 오류 처리
```python
async def robust_agent_execution(agent: Agent, context: Context):
    try:
        result = await agent.execute(context)
        return result
    except Exception as e:
        logger.error(f"에이전트 {agent.name} 실패: {e}")
        return fallback_result()
```

---

## 🎯 성능 아키텍처

### 최적화 전략

#### 1. 데이터 샘플링
- **LLM 분석**: 비용이 많이 드는 작업에 대표 샘플 사용
- **통계적 분석**: 정확한 지표를 위해 전체 데이터셋 처리
- **균형**: 성능 최적화하면서 통계적 유효성 유지

#### 2. 캐싱 전략
```python
class ResultCache:
    def __init__(self):
        self.cache = {}
    
    def get(self, key: str) -> Optional[Any]:
        return self.cache.get(key)
    
    def set(self, key: str, value: Any):
        self.cache[key] = value
```

#### 3. 병렬 처리
- **에이전트 병렬화**: 독립적인 에이전트를 동시에 실행
- **데이터 청킹**: 대규모 데이터셋을 병렬 청크로 처리
- **리소스 관리**: 동시 작업 제어

### 메모리 관리

#### 1. 데이터 스트리밍
```python
def process_large_dataset(file_path: str, chunk_size: int = 1000):
    for chunk in pd.read_csv(file_path, chunksize=chunk_size):
        yield process_chunk(chunk)
```

#### 2. 가비지 컬렉션
```python
import gc

def cleanup_memory():
    gc.collect()
    # 큰 변수 정리
    del large_dataframe
```

---

## 🔐 보안 아키텍처

### 데이터 보호

#### 1. API 보안
- **자격 증명 관리**: 환경 변수 기반 구성
- **API 키 순환**: 키 순환 및 업데이트 지원
- **속도 제한**: API 남용 방지 및 비용 관리

#### 2. 데이터 개인정보 보호
- **로컬 처리**: 민감한 데이터를 온프레미스에 보관
- **데이터 익명화**: LLM 처리 전 PII 제거
- **감사 로깅**: 데이터 액세스 및 처리 추적

### 액세스 제어

#### 1. 인증
```python
class APIAuthenticator:
    def __init__(self, api_key: str):
        self.api_key = api_key
    
    def authenticate(self, request: Request) -> bool:
        return request.headers.get('Authorization') == f'Bearer {self.api_key}'
```

#### 2. 권한 부여
```python
class RoleBasedAccess:
    def __init__(self, user_roles: Dict[str, List[str]]):
        self.user_roles = user_roles
    
    def has_permission(self, user: str, action: str) -> bool:
        return action in self.user_roles.get(user, [])
```

---

## 📈 확장성 아키텍처

### 수평적 확장

#### 1. 에이전트 분산
```python
class DistributedAgentManager:
    def __init__(self, worker_nodes: List[str]):
        self.worker_nodes = worker_nodes
    
    async def distribute_agents(self, agents: List[Agent]):
        # 워커 노드에 에이전트 분산
        pass
```

#### 2. 로드 밸런싱
```python
class LoadBalancer:
    def __init__(self):
        self.node_weights = {}
    
    def select_node(self) -> str:
        # 가장 적게 로드된 노드 선택
        return min(self.node_weights, key=self.node_weights.get)
```

### 수직적 확장

#### 1. 리소스 최적화
- **메모리**: 데이터 구조 및 처리 최적화
- **CPU**: 병렬 처리 및 벡터화
- **저장소**: 효율적인 데이터 형식 및 압축

#### 2. 성능 모니터링
```python
class PerformanceMonitor:
    def __init__(self):
        self.metrics = {}
    
    def track_metric(self, name: str, value: float):
        self.metrics[name] = value
    
    def get_performance_report(self) -> Dict[str, float]:
        return self.metrics
```

---

## 🔧 구성 아키텍처

### 환경 관리

#### 1. 구성 계층
```python
class ConfigManager:
    def __init__(self):
        self.config = {
            'default': load_default_config(),
            'environment': load_env_config(),
            'user': load_user_config(),
        }
    
    def get(self, key: str) -> Any:
        # 가장 구체적인 구성 반환
        return self.config['user'].get(key) or \
               self.config['environment'].get(key) or \
               self.config['default'].get(key)
```

#### 2. 동적 구성
```python
class DynamicConfig:
    def __init__(self):
        self.config = {}
        self.watchers = []
    
    def watch(self, key: str, callback: Callable):
        self.watchers.append((key, callback))
    
    def update(self, key: str, value: Any):
        self.config[key] = value
        self.notify_watchers(key, value)
```

---

## 🧪 테스팅 아키텍처

### 테스트 전략

#### 1. 단위 테스팅
```python
class TestAgent:
    def test_agent_execution(self):
        agent = DataUnderstandingAgent()
        result = agent.execute(test_context)
        assert result.success == True
```

#### 2. 통합 테스팅
```python
class TestPipeline:
    def test_full_pipeline(self):
        pipeline = AnalysisPipeline()
        result = pipeline.run(test_data)
        assert result.reports_generated == True
```

#### 3. 성능 테스팅
```python
class TestPerformance:
    def test_large_dataset_processing(self):
        start_time = time.time()
        result = process_large_dataset(large_csv_file)
        execution_time = time.time() - start_time
        assert execution_time < max_acceptable_time
```

---

## 📚 문서화 아키텍처

### 코드 문서화

#### 1. API 문서화
```python
def analyze_conversion_performance(
    data: pd.DataFrame,
    experiment_column: str,
    control_column: str
) -> Dict[str, Any]:
    """
    실험 그룹과 대조 그룹 간의 전환 성과를 분석합니다.
    
    Args:
        data: 캠페인 데이터가 포함된 DataFrame
        experiment_column: 실험 그룹의 열 이름
        control_column: 대조 그룹의 열 이름
    
    Returns:
        전환 지표 및 통계적 유의성을 포함한 딕셔너리
    
    Raises:
        ValueError: 필수 열이 누락된 경우
        StatisticalError: 분석에 충분한 데이터가 없는 경우
    """
```

#### 2. 아키텍처 문서화
- **시스템 개요**: 고수준 아키텍처 설명
- **구성 요소 세부사항**: 개별 구성 요소 사양
- **통합 가이드**: 구성 요소가 함께 작동하는 방법
- **배포 가이드**: 프로덕션 배포 지침

---

*아키텍처 문서 by saintwo - 마지막 업데이트: 2025년 10월*