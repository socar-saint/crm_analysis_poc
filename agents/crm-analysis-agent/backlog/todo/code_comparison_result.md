# 코드 비교 결과: 이전 폴더 vs 현재 폴더

## 📊 비교 결과

### 파일 구조
- 이전 폴더: `/Users/saint/Jupyter/1. Task/crm-analysis-agent`
- 현재 폴더: `/Users/saint/ai-agent-platform/agents/crm-analysis-agent`

### 동일한 부분
1. **main.py**: 2011 lines (이전) vs 2009 lines (현재) - 거의 동일
2. **comprehensive_html_report.py**: 1607 lines (이전) vs 1608 lines (현재) - 거의 동일
3. **funnel_strategy_agent 정의**: 완전히 동일
4. **generate_group_strategy 함수**: 완전히 동일

### 발견된 문제
**이전 폴더의 HTML 리포트도 "Agent 분석 결과 대기 중" 표시됨**
- 파일: `outputs/reports/20251021/251021_1621_executive_summary_report.html`
- 내용: 상위/중위/하위 그룹 모두 "Agent 분석 결과 대기 중"

## 🔍 근본 원인 분석

### 문제의 핵심

**Agent가 반환하는 JSON** (터미널 출력):
```json
{
  "high_performance_group (Lift ≥ 5.29%p)": {
    "strategy": "...",
    "message_pattern": "...",
    "common_features": [...],
    "recommendations": [...],
    "keywords": [...],
    "funnel_top_messages": [...]
  }
}
```

**HTML 리포트가 찾는 키** (Line 1083):
```python
group_key = f"{group_type}_performance_group"  
# "high_performance_group"
```

**키가 일치하지 않음!**

### 왜 이런 문제가 발생하는가?

Agent 프롬프트(Line 1103-1138)에서:
```
- **도구에서 제공하는 실제 q33, q67 값을 사용하여 그룹 제목을 생성하세요**
- **추출된 값으로 그룹 제목 생성** (예: "상위 그룹 (Lift ≥ X.X%p)")
```

Agent가 이 지시를 따르면서:
- JSON의 그룹 제목에 특수문자 포함 → `"high_performance_group (Lift ≥ 5.29%p)"`
- HTML 리포트는 표준 키만 찾음 → `"high_performance_group"`

## 💡 해결 방안

### 수정할 파일
1. `core/reporting/comprehensive_html_report.py` Line 1080-1135
2. `main.py` Line 1103-1138 (Agent 프롬프트)

### 수정 방법
JSON 키 정규화 로직 추가:
```python
# comprehensive_html_report.py Line 1056-1066 수정

if self.agent_results and 'funnel_strategy_analysis' in self.agent_results:
    try:
        import json
        strategy_result = self.agent_results['funnel_strategy_analysis']
        if isinstance(strategy_result, str):
            strategy_data = json.loads(strategy_result)
        else:
            strategy_data = strategy_result
        
        # 🔥 핵심 추가: JSON 키 정규화
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
        
        strategy_data = normalized_data if normalized_data else strategy_data
        
    except Exception as e:
        print(f"⚠️ 전략 데이터 파싱 실패: {e}")
        strategy_data = {}
```

## 🎯 확인 사항

이전 폴더도 같은 문제를 가지고 있으므로:
- 이전 폴더에서도 수정이 필요함
- 또는 이전 폴더도 정상 작동하지 않았던 것

**결론**: 두 폴더 모두 같은 버그를 가지고 있음. 지금 수정 필요!

