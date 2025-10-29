# 도메인 이해도 및 Context 전달 상세 분석

## 1. 도메인 이해도를 누가 파악하는가?

### 담당자: Data Understanding Agent
- **파일 위치**: `main.py`의 `data_understanding_agent`
- **프롬프트**: `core/llm/prompt_engineering.py`의 `get_data_understanding_prompt()`
- **도구**: `validate_csv_terms_with_llm`, `get_domain_glossary`

### 판단 기준과 로직
```python
# core/llm/simple_llm_terminology_tools.py Line 42-44
# 상위 10개 용어를 한 번에 분석
terms_to_analyze = all_terms[:10]
print(f"🚀 배치 용어 분석 중: {len(terms_to_analyze)}개 용어 (API 호출 1회)")
```

**판단 기준:**
1. **용어 이해도 점수**: 0-100점 (70% 미만 시 도메인 학습 권장)
2. **용어사전 일치 여부**: `all_domain_terms.get(term, None)`
3. **도메인 관련성**: 용어사전에 없는 용어의 도메인 관련성 평가

## 2. 용어 비교 로직

### ❌ 잘못된 이해: 모든 용어를 비교하지 않음
```python
# core/llm/simple_llm_terminology_tools.py Line 43
terms_to_analyze = all_terms[:10]  # 상위 10개만 분석
```

**실제 로직:**
1. CSV에서 2,219개 고유 용어 추출
2. **상위 10개 용어만** LLM으로 분석
3. 용어사전 44개 용어와 비교
4. 나머지 2,209개 용어는 분석하지 않음

### 용어 비교 과정
```python
# Line 57: 각 용어별로 용어사전과 비교
dictionary_definition = all_domain_terms.get(term, None)

# Line 71-72: LLM에게 전체 용어사전 전달
도메인 용어사전:
{json.dumps(all_domain_terms, ensure_ascii=False, indent=2)}
```

## 3. 구조화된 Context 관리

### AnalysisContext 클래스 (main.py Line 83-135)
```python
class AnalysisContext:
    def __init__(self):
        # 용어 이해도 결과
        self.terminology_analysis = None
        # 기타 분석 결과들...
```

### 순차적 Agent 간 데이터 전달 (main.py Line 1021-1043)
```python
# 응답을 컨텍스트에 저장
if agent_name == "data_understanding":
    context.data_info = response
elif agent_name == "category_analysis":
    context.category_analysis = response
elif agent_name == "funnel_segment_analysis":
    context.funnel_segment_analysis = response
# ... 다른 Agent들
```

## 4. terminology_analysis와 도메인 이해도 차이

### terminology_analysis
- **정의**: `AnalysisContext`의 속성 (Line 115)
- **용도**: 용어 검증 결과를 저장하는 변수
- **현재 상태**: **정의만 있고 실제 사용되지 않음**

### 도메인 이해도 검증
- **실행**: `validate_csv_terms_with_llm` 함수
- **결과**: LLM이 평가한 용어 이해도 점수
- **저장**: **terminology_analysis에 저장되지 않음**

## 5. 용어 검증이 전달되지 않는 이유

### 문제점 1: terminology_analysis에 저장되지 않음
```python
# main.py Line 1021-1022
if agent_name == "data_understanding":
    context.data_info = response  # 전체 응답만 저장
    # terminology_analysis는 업데이트되지 않음
```

### 문제점 2: context_info에 포함되지 않음
```python
# main.py Line 1207-1222: context_info 구성
context_info = f"""
이전 분석 결과들:
- 데이터 구조: {context.data_info}
- 카테고리 분석: {context.category_analysis}
# terminology_analysis는 포함되지 않음
"""
```

### 문제점 3: Agent 도구 호출 결과가 Context에 반영되지 않음
- `validate_csv_terms_with_llm` 호출 결과가 `context.terminology_analysis`에 저장되지 않음
- 도구 실행 결과와 Agent 응답이 분리되어 있음

## 🔧 해결 방안

### 1. terminology_analysis 저장 로직 추가
```python
# main.py 수정 필요
if agent_name == "data_understanding":
    context.data_info = response
    # 용어 검증 결과도 별도로 저장 필요
```

### 2. context_info에 용어 이해도 포함
```python
context_info = f"""
이전 분석 결과들:
- 용어 이해도: {context.terminology_analysis}
- 데이터 구조: {context.data_info}
"""
```

### 3. 용어 검증 결과 활용
- 다른 Agent들이 용어 이해도를 참고할 수 있도록 전달
- 미이해 용어에 대한 추가 학습 메커니즘 구현
