# Funnel 분석 결과가 나오지 않는 문제 수정 계획

## 🔍 문제 원인

### 현재 상황
HTML 리포트에서:
- 상위/중위/하위 그룹 전략이 모두 "Agent 분석 결과 대기 중"으로 표시
- 실제 Agent는 실행되고 JSON도 생성되지만 리포트에 반영되지 않음

### 근본 원인

#### 1. JSON 키 불일치 문제

**Agent가 반환하는 JSON** (터미널 출력):
```json
{
  "high_performance_group (Lift ≥ 5.29%p)": {
    "strategy": "...",
    "message_pattern": "...",
    ...
  }
}
```

**HTML 리포트가 찾는 키**:
```python
group_key = f"{group_type}_performance_group"  # "high_performance_group"
```

**키가 다름!**
- Agent: `"high_performance_group (Lift ≥ 5.29%p)"`  ← 특수문자 포함
- 리포트: `"high_performance_group"`  ← 특수문자 없음

#### 2. JSON 파일과 Agent 응답의 불일치

**JSON 파일** (`251027_1649_funnel_quantile_data.json`):
```json
{
  "high_performance_group": {
    "funnels": [...],
    "top_messages": [...]
  }
}
```
→ 표준 키 사용 ✅

**Agent 응답** (터미널 출력):
```json
{
  "high_performance_group (Lift ≥ 5.29%p)": {...}
}
```
→ 특수문자 포함 키 사용 ❌

### 문제 플로우

1. ✅ `prepare_funnel_quantile_data` 도구 실행 → JSON 파일 생성 (표준 키)
2. ✅ Agent가 실행되어 JSON 응답 생성 (특수문자 포함 키)
3. ✅ context.funnel_strategy_analysis에 저장
4. ❌ HTML 리포트 생성 시 JSON 파싱
   - `json.loads(strategy_result)` → 성공
   - `strategy_data.get('high_performance_group')` → None (키가 다름!)
5. ❌ fallback 코드 실행 → "Agent 분석 결과 대기 중" 표시

## 💡 해결 방안

### Option 1: Agent 응답 형식 수정 (가장 깔끔)
**위치**: `main.py` Line 1102-1139

Agent가 반환하는 JSON을 표준 키로만 사용하도록 수정:
```python
{
  "high_performance_group": {...},
  "medium_performance_group": {...},
  "low_performance_group": {...}
}
```

**구체적 수정**:
- `main.py` Line 1111-1113의 프롬프트 수정
- "절대 하드코딩된 기준값(1.5%p, 0.2%p 등)을 사용하지 마세요" 제거
- 그룹 제목은 HTML에서 표시하고, JSON 키는 표준화

### Option 2: HTML 리포트 파싱 로직 개선 (빠른 수정)
**위치**: `core/reporting/comprehensive_html_report.py` Line 1056-1120

특수문자를 포함한 키도 처리하도록 수정:
```python
# Line 1083 수정
group_key = f"{group_type}_performance_group"

# 특수문자 포함 키 처리
matching_keys = [k for k in strategy_data.keys() if f"{group_type}_performance_group" in k]
if matching_keys:
    group_key = matching_keys[0]
    group_info = strategy_data[group_key]
```

### Option 3: JSON 키 정규화 (중간 수정)
`json.loads()` 후 키를 정규화:
```python
# Line 1060-1066 수정
strategy_data = json.loads(strategy_result)

# 키 정규화
normalized_data = {}
for key, value in strategy_data.items():
    if 'high_performance_group' in key:
        normalized_data['high_performance_group'] = value
    elif 'medium_performance_group' in key:
        normalized_data['medium_performance_group'] = value
    elif 'low_performance_group' in key:
        normalized_data['low_performance_group'] = value

strategy_data = normalized_data
```

## 🎯 추천 방안

**Option 1 (Agent 수정)**: 가장 깔끔하고 명확
**Option 2 (파싱 개선)**: 가장 빠름
**Option 3 (정규화)**: 중간 복잡도

### 먼저 Option 2로 빠르게 수정하고, 나중에 Option 1로 개선

## 📝 수정할 파일

1. `core/reporting/comprehensive_html_report.py` Line 1056-1120
2. `main.py` Line 1102-1139 (Agent 프롬프트)

## 🚀 수정 계획

### Step 1: HTML 리포트 파싱 로직 수정 (빠른 수정)
```python
# comprehensive_html_report.py Line 1080-1120

def generate_group_strategy(group_type, group_df, q_range):
    group_key = f"{group_type}_performance_group"
    
    # 특수문자를 포함한 키도 찾기
    if strategy_data:
        # 표준 키 먼저 시도
        if group_key in strategy_data:
            group_info = strategy_data[group_key]
        else:
            # 특수문자 포함 키 찾기
            matching_keys = [k for k in strategy_data.keys() if group_key in k]
            if matching_keys:
                group_info = strategy_data[matching_keys[0]]
            else:
                group_info = None
    else:
        group_info = None
    
    if group_info:
        # 기존 로직...
    else:
        # fallback 로직...
```

### Step 2: Agent 프롬프트 수정 (나중에)
JSON 형식 명확화

---

## 📊 영향 범위

**수정 전**:
- Agent 실행: ✅ 성공
- JSON 생성: ✅ 성공  
- HTML 리포트: ❌ "Agent 분석 결과 대기 중"

**수정 후**:
- Agent 실행: ✅ 성공
- JSON 생성: ✅ 성공
- HTML 리포트: ✅ 실제 분석 결과 표시

