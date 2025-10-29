# 이전 폴더 vs 현재 폴더 코드 비교

## 🔍 발견된 차이점

### 1. JSON 키 정규화 로직 (차이점 1)

**이전 폴더** (Line 1056-1066):
```python
if self.agent_results and 'funnel_strategy_analysis' in self.agent_results:
    try:
        import json
        strategy_result = self.agent_results['funnel_strategy_analysis']
        if isinstance(strategy_result, str):
            strategy_data = json.loads(strategy_result)
        else:
            strategy_data = strategy_result
    except Exception as e:
        print(f"⚠️ 전략 데이터 파싱 실패: {e}")
        strategy_data = {}
```

**현재 폴더** (Line 1056-1080):
```python
if self.agent_results and 'funnel_strategy_analysis' in self.agent_results:
    try:
        import json
        strategy_result = self.agent_results['funnel_strategy_analysis']
        if isinstance(strategy_result, str):
            strategy_data = json.loads(strategy_result)
        else:
            strategy_data = strategy_result
        
        # 🔥 핵심 추가: JSON 키 정규화 (특수문자 포함 키 처리)
        normalized_data = {}
        for key in list(strategy_data.keys()):
            normalized_key = None
            if 'high_performance_group' in key:
                normalized_key = 'high_performance_group'
            elif 'medium_performance_group' in key:
                normalized_key = 'medium_performance_group'
            elif 'low_performance_group' in key:
                normalized_key = 'low_performance_group'
            
            if normalized_key:
                normalized_data[normalized_key] = strategy_data[key]
        
        # 정규화된 데이터가 있으면 사용, 없으면 원본 사용
        strategy_data = normalized_data if normalized_data else strategy_data
        
    except Exception as e:
        print(f"⚠️ 전략 데이터 파싱 실패: {e}")
        strategy_data = {}
```

**차이점**: 현재 폴더에는 JSON 키 정규화 로직이 추가됨

### 2. 디버깅 로그 (차이점 2)

**이전 폴더** (Line 1068-1078):
```python
print(f"🔍 파싱된 strategy_data:")
print(f"  - strategy_data 존재: {bool(strategy_data)}")
if strategy_data:
    print(f"  - strategy_data 키들: {list(strategy_data.keys())}")
    if 'high_performance_group' in strategy_data:
        high_funnels = strategy_data['high_performance_group'].get('funnels', [])
        high_funnel_names = [f['funnel'] for f in high_funnels] if high_funnels else []
        print(f"  - 상위 그룹 퍼널: {high_funnel_names}")
else:
    print(f"  - strategy_data가 비어있음")
```

**현재 폴더** (Line 1086-1099):
```python
print(f"🔍 파싱된 strategy_data:")
print(f"  - strategy_data 존재: {bool(strategy_data)}")
if strategy_data:
    print(f"  - strategy_data 키들: {list(strategy_data.keys())}")
    if 'high_performance_group' in strategy_data:
        high_info = strategy_data['high_performance_group']
        print(f"  - high_performance_group 키: {list(high_info.keys())}")
        print(f"  - strategy: {high_info.get('strategy', 'None')[:100]}")
    else:
        print(f"  - ❌ 'high_performance_group' 키가 없음!")
        print(f"  - 실제 키들: {list(strategy_data.keys())}")
else:
    print(f"  - strategy_data가 비어있음")
```

**차이점**: 현재 폴더의 디버깅 로그가 더 상세함

### 3. 퍼널 태그 추출 로직 (차이점 3)

**이전 폴더** (Line 1086-1094):
```python
# 퍼널 태그 - strategy_data에서 퍼널 목록 추출
funnel_names = []
if 'funnels' in group_info:
    funnel_names = [funnel['funnel'] for funnel in group_info['funnels']]
else:
    # fallback: group_df 사용
    funnel_names = [row["퍼널"] for _, row in group_df.iterrows()]
```

**현재 폴더** (Line 1107-1110):
```python
# 퍼널 태그 - group_df에서 퍼널 목록 추출 (항상 group_df 사용)
funnel_names = [row["퍼널"] for _, row in group_df.iterrows()] if not group_df.empty else []
```

**차이점**: 이전 폴더는 strategy_data의 funnels를 우선적으로 사용하고, 현재 폴더는 항상 group_df 사용

## 📊 핵심 차이점 요약

1. ✅ **JSON 키 정규화**: 현재 폴더에만 존재 (1065-1080)
2. ✅ **디버깅 로그**: 현재 폴더가 더 상세
3. ⚠️ **퍼널 태그 추출**: 로직이 완전히 다름
   - 이전: strategy_data의 funnels 우선 → group_df fallback
   - 현재: 항상 group_df만 사용

## 🚨 문제 발견

이전 폴더 코드에서도 "Agent 분석 결과 대기 중"으로 표시된다는 것은:
- 정규화 로직 추가로는 해결되지 않음
- 근본적인 문제는 다른 곳에 있음

## 💡 예상 원인

1. `agent_results`에 `funnel_strategy_analysis`가 없거나
2. `strategy_data` 파싱은 성공했지만 키 매칭 실패
3. `generate_group_strategy` 함수 내부 로직 문제

