"""데이터 분석 함수들 (통계 기반 + LLM 기반)"""

import pandas as pd
import numpy as np
import json
import re
from collections import Counter
from typing import Dict, Any, List
from config.settings import settings, azure_llm  # azure_llm 싱글톤 import

# =============================================================================
# 1. 통계 기반 분석 함수들
# =============================================================================

def analyze_conversion_performance(df) -> Dict[str, Any]:
    """전환율 성과 분석"""
    try:
        # 실험군 vs 대조군 전환율 비교
        experiment_conversion = df['실험군_예약전환율'].mean()
        control_conversion = df['대조군_예약전환율'].mean()
        
        # 퍼널별 성과 분석
        funnel_analysis = df.groupby('퍼널')['실험군_예약전환율'].agg(['mean', 'count']).round(3)
        
        # 채널별 성과 분석
        channel_analysis = df.groupby('채널')['실험군_예약전환율'].agg(['mean', 'count']).round(3)
        
        return {
            "status": "success",
            "experiment_conversion_rate": float(experiment_conversion),
            "control_conversion_rate": float(control_conversion),
            "lift": float(experiment_conversion - control_conversion),
            "funnel_analysis": funnel_analysis.to_dict(),
            "channel_analysis": channel_analysis.to_dict(),
            "message": f"실험군 전환율: {experiment_conversion:.2f}%, 대조군: {control_conversion:.2f}%"
        }
    except Exception as e:
        return {"status": "error", "error_message": str(e)}

def analyze_message_effectiveness(df) -> Dict[str, Any]:
    """문구별 효과성 분석"""
    try:
        # 문구별 전환율 분석
        message_analysis = df.groupby('문구')['실험군_예약전환율'].agg(['mean', 'count']).round(3)
        best_message = message_analysis['mean'].idxmax()
        best_rate = message_analysis['mean'].max()
        
        return {
            "status": "success",
            "best_message": str(best_message),
            "best_conversion_rate": float(best_rate),
            "total_messages": int(len(message_analysis)),
            "message_analysis": message_analysis.to_dict(),
            "message": f"최고 성과 문구: {best_message[:50]}... (전환율: {best_rate:.2f}%)"
        }
    except Exception as e:
        return {"status": "error", "error_message": str(e)}

def analyze_funnel_performance(df) -> Dict[str, Any]:
    """퍼널별 성과 분석"""
    try:
        # 퍼널별 상세 분석
        funnel_stats = df.groupby('퍼널').agg({
            '실험군_발송': 'sum',
            '실험군_1일이내_예약생성': 'sum',
            '실험군_예약전환율': 'mean',
            '대조군_예약전환율': 'mean'
        }).round(3)
        
        # 실험군 vs 대조군 비교
        funnel_stats['lift'] = funnel_stats['실험군_예약전환율'] - funnel_stats['대조군_예약전환율']
        
        return {
            "status": "success",
            "funnel_stats": funnel_stats.to_dict(),
            "message": "퍼널별 성과 분석 완료"
        }
    except Exception as e:
        return {"status": "error", "error_message": str(e)}

def analyze_funnel_message_effectiveness(df) -> Dict[str, Any]:
    """퍼널별 문구 효과성 분석"""
    try:
        funnel_message_analysis = df.groupby(['퍼널', '문구'])['실험군_예약전환율'].agg(['mean', 'count']).round(3)
        funnel_message_analysis = funnel_message_analysis.reset_index()
        
        best_messages_by_funnel = {}
        for funnel in df['퍼널'].unique():
            if pd.isna(funnel):
                continue
                
            funnel_data = funnel_message_analysis[funnel_message_analysis['퍼널'] == funnel]
            if len(funnel_data) > 0:
                best_message = funnel_data.loc[funnel_data['mean'].idxmax()]
                best_messages_by_funnel[funnel] = {
                    'best_message': best_message['문구'],
                    'conversion_rate': float(best_message['mean']),
                    'count': int(best_message['count'])
                }
        
        return {
            "status": "success",
            "best_messages_by_funnel": best_messages_by_funnel,
            "message": "퍼널별 문구 효과성 분석 완료"
        }
    except Exception as e:
        return {"status": "error", "error_message": str(e)}

def analyze_message_patterns_by_funnel(df) -> Dict[str, Any]:
    """퍼널별 문구 패턴 분석"""
    try:
        pattern_analysis = {}
        
        for funnel in df['퍼널'].unique():
            if pd.isna(funnel):
                continue
                
            funnel_data = df[df['퍼널'] == funnel]
            funnel_data_sorted = funnel_data.sort_values('실험군_예약전환율', ascending=False)
            
            # 상위 5개 문구 분석
            top_messages = funnel_data_sorted.head(5)
            
            # 공통 키워드 분석
            all_messages = funnel_data['문구'].dropna().str.cat(sep=' ')
            
            # 간단한 키워드 추출
            korean_words = re.findall(r'[가-힣]{2,}', all_messages)
            keyword_counts = Counter(korean_words)
            top_keywords = keyword_counts.most_common(10)
            
            pattern_analysis[funnel] = {
                'total_messages': len(funnel_data),
                'top_messages': top_messages[['문구', '실험군_예약전환율']].to_dict('records'),
                'top_keywords': top_keywords,
                'avg_conversion_rate': float(funnel_data['실험군_예약전환율'].mean())
            }
        
        return {
            "status": "success",
            "pattern_analysis": pattern_analysis,
            "message": "퍼널별 문구 패턴 분석 완료"
        }
    except Exception as e:
        return {"status": "error", "error_message": str(e)}

# =============================================================================
# 2. LLM 기반 분석 함수들
# =============================================================================

def analyze_single_message_llm(message, funnel, conversion_rate, channel) -> Dict[str, Any]:
    """단일 메시지를 LLM이 분석"""
    
    prompt = f"""
    다음 쏘카 CRM 마케팅 메시지를 분석해주세요:
    
    **메시지**: {message}
    **퍼널**: {funnel}
    **전환율**: {conversion_rate}%
    **채널**: {channel}
    
    다음 관점에서 분석해주세요:
    
    1. **문장 구조 분석**: 문장 길이, 복잡도, 유형, 흐름
    2. **핵심 키워드 분석**: 전환율에 기여하는 핵심 단어들
    3. **톤앤매너 분석**: 전체적인 톤, 감정적 어필, 고객과의 거리감
    4. **퍼널별 적합성**: 해당 퍼널 단계에 적합한지
    5. **전환율 기여 요소**: 효과적인 부분과 개선점
    
    JSON 형식으로 답변해주세요:
    {{
        "sentence_structure": {{
            "length": "문장 길이 평가",
            "complexity": "복잡도 평가",
            "type": "문장 유형",
            "flow": "문장 흐름 평가"
        }},
        "keywords": {{
            "core_words": ["핵심 단어1", "핵심 단어2"],
            "emotional_words": ["감정 단어1", "감정 단어2"],
            "action_words": ["행동 유도 단어1", "행동 유도 단어2"]
        }},
        "tone_manner": {{
            "overall_tone": "전체 톤",
            "emotional_appeal": "감정적 어필 방식",
            "customer_distance": "고객과의 거리감"
        }},
        "funnel_fit": {{
            "suitability": "퍼널 적합성",
            "target_alignment": "타겟 고객 정렬도"
        }},
        "conversion_factors": {{
            "strengths": ["강점1", "강점2"],
            "weaknesses": ["약점1", "약점2"],
            "improvement_suggestions": ["개선 제안1", "개선 제안2"]
        }},
        "effectiveness_score": 85,
        "reasoning": "전체적인 분석 근거"
    }}
    """
    
    try:
        response = azure_llm.completion(
            model=f"azure/{settings.AZURE_OPENAI_DEPLOYMENT_NAME}",
            messages=[{"role": "user", "content": prompt}],
            api_key=settings.AZURE_OPENAI_API_KEY,
            api_base=settings.AZURE_OPENAI_ENDPOINT,
            api_version=settings.AZURE_OPENAI_API_VERSION,
            temperature=0.3
        )
        
        response_text = response.choices[0].message.content
        
        # JSON 추출
        json_start = response_text.find('{')
        json_end = response_text.rfind('}') + 1
        
        if json_start != -1 and json_end != -1:
            json_str = response_text[json_start:json_end]
            analysis_result = json.loads(json_str)
            return analysis_result
        else:
            return {"error": "JSON 파싱 실패"}
            
    except Exception as e:
        return {"error": f"분석 중 오류: {str(e)}"}

def analyze_messages_by_funnel_llm(df, sample_size=3) -> Dict[str, Any]:
    """LLM이 퍼널별로 메시지를 직접 분석"""
    
    try:
        funnel_analyses = {}
        
        for funnel in df['퍼널'].unique():
            if pd.isna(funnel):
                continue
                
            # 해당 퍼널의 데이터만 필터링
            funnel_data = df[df['퍼널'] == funnel]
            funnel_data_sorted = funnel_data.sort_values('실험군_예약전환율', ascending=False)
            
            # 상위 샘플 선택
            sample_data = funnel_data_sorted.head(sample_size)
            
            funnel_analyses[funnel] = {
                'total_messages': len(funnel_data),
                'sample_size': len(sample_data),
                'analyses': []
            }
            
            # 각 메시지별로 LLM 분석
            for idx, row in sample_data.iterrows():
                analysis = analyze_single_message_llm(
                    message=row['문구'],
                    funnel=funnel,
                    conversion_rate=row['실험군_예약전환율'],
                    channel=row['채널']
                )
                
                if 'error' not in analysis:
                    funnel_analyses[funnel]['analyses'].append({
                        'message': row['문구'],
                        'conversion_rate': row['실험군_예약전환율'],
                        'channel': row['채널'],
                        'analysis': analysis
                    })
        
        return {
            "status": "success",
            "funnel_analyses": funnel_analyses,
            "message": "LLM 기반 퍼널별 문구 분석 완료"
        }
        
    except Exception as e:
        return {"status": "error", "error_message": str(e)}

# def analyze_message_effectiveness_reasons_global_batch(df) -> Dict[str, Any]:
    """문구 효과성 이유 분석 (전체 퍼널 배치 처리 + 인사이트 축적)"""
    
    try:
        from sklearn.feature_extraction.text import TfidfVectorizer
        from sklearn.metrics.pairwise import cosine_similarity
        import numpy as np
        
        print("🔍 전체 퍼널 배치 문구 효과성 분석 시작 (인사이트 축적)...")
        
        # 전체 데이터 준비
        all_funnel_data = []
        funnel_stats = {}
        
        # 퍼널별 데이터 수집
        for funnel in df['퍼널'].unique():
            if pd.isna(funnel):
                continue
                
            print(f"📊 {funnel} 퍼널 데이터 수집...")
            
            # 해당 퍼널의 데이터만 필터링
            funnel_data = df[df['퍼널'] == funnel]
            funnel_data_sorted = funnel_data.sort_values('실험군_예약전환율', ascending=False)
            
            if len(funnel_data_sorted) < 2:
                continue
            
            # 퍼널별 통계
            funnel_avg = funnel_data['실험군_예약전환율'].mean()
            funnel_stats[funnel] = {
                'avg_conversion': funnel_avg,
                'total_messages': len(funnel_data),
                'max_conversion': funnel_data['실험군_예약전환율'].max(),
                'min_conversion': funnel_data['실험군_예약전환율'].min()
            }
            
            # 상위 5개 + 하위 5개 문구 선택 (전체 배치를 위해 개수 줄임)
            top_messages = funnel_data_sorted.head(5)
            bottom_messages = funnel_data_sorted.tail(5)
            
            # 상위 문구 데이터
            for i, (idx, row) in enumerate(top_messages.iterrows()):
                all_funnel_data.append({
                    "funnel": funnel,
                    "message": row['문구'],
                    "conversion_rate": row['실험군_예약전환율'],
                    "length": len(row['문구']),
                    "rank": i + 1,
                    "group": "high_performing",
                    "funnel_avg": funnel_avg
                })
            
            # 하위 문구 데이터
            for i, (idx, row) in enumerate(bottom_messages.iterrows()):
                all_funnel_data.append({
                    "funnel": funnel,
                    "message": row['문구'],
                    "conversion_rate": row['실험군_예약전환율'],
                    "length": len(row['문구']),
                    "rank": i + 1,
                    "group": "low_performing",
                    "funnel_avg": funnel_avg
                })
        
        print(f"🚀 전체 배치 분석 중: {len(all_funnel_data)}개 문구, {len(funnel_stats)}개 퍼널 (API 호출 1회)")
        
        # 전체 배치 프롬프트 생성
        batch_prompt = f"""
        다음 쏘카 CRM 문구들을 전체 퍼널에서 종합 분석해주세요:
        
        퍼널별 통계:
        {json.dumps(funnel_stats, ensure_ascii=False, indent=2)}
        
        분석할 문구들 (퍼널별 상위/하위 대조):
        {json.dumps(all_funnel_data, ensure_ascii=False, indent=2)}
        
        각 문구에 대해 다음을 분석해주세요:
        
        1. **텍스트 구조적 특징** (수치 기반):
           - 문장 길이의 효과성 (퍼널 평균 대비 분석)
           - 특수문자 사용의 효과
           - 숫자 사용의 효과
           - 문장 구조의 효과
        
        2. **심리적 어필 요소** (구체적 이유):
           - 감정적 자극 요소와 효과
           - 긴급성/제한성 어필의 효과
           - 혜택/할인 강조의 효과
        
        3. **퍼널별 적합성** (데이터 기반):
           - 퍼널 평균 대비 성과 분석
           - 고객 심리 상태와의 매칭도
           - 퍼널 단계별 특성과의 일치도
        
        4. **행동 유도 요소** (구체적 분석):
           - 명확한 행동 지시의 효과
           - 클릭 유도 문구의 효과
           - 다음 단계 안내의 효과
        
        5. **수치적 근거** (중요):
           - 전환율이 높은/낮은 구체적 이유
           - 다른 문구 대비 우수한/부족한 점
           - 성과 지표와 근거
        
        다음 JSON 형식으로 답변해주세요:
        {{
            "global_analysis": {{
                "total_funnels": {len(funnel_stats)},
                "total_messages_analyzed": {len(all_funnel_data)},
                "analysis_type": "global_batch_with_insights"
            }},
            "message_analyses": [
                {{
                    "funnel": "T1",
                    "message": "문구1",
                    "conversion_rate": 12.5,
                    "group": "high_performing",
                    "text_structure": {{
                        "length": 45,
                        "length_analysis": "문장 길이 45자의 효과성 분석",
                        "special_characters": "특수문자 사용 분석",
                        "numbers": "숫자 사용 분석",
                        "structure": "문장 구조 분석"
                    }},
                    "psychological_appeal": {{
                        "emotional_triggers": ["감정 자극 요소1", "감정 자극 요소2"],
                        "urgency": "긴급성 어필 정도",
                        "benefit_emphasis": "혜택 강조 정도"
                    }},
                    "funnel_fit": {{
                        "customer_state": "고객 심리 상태",
                        "message_alignment": "메시지 적합성",
                        "funnel_stage": "퍼널 단계별 특성",
                        "performance_vs_average": "평균 대비 성과"
                    }},
                    "action_induction": {{
                        "clear_instructions": "명확한 행동 지시",
                        "click_encouragement": "클릭 유도 요소",
                        "next_step_guidance": "다음 단계 안내"
                    }},
                    "numerical_evidence": {{
                        "conversion_rate": 12.5,
                        "performance_reason": "전환율 12.5%가 높은/낮은 구체적 이유",
                        "comparative_advantage": "다른 문구 대비 우수한/부족한 점",
                        "key_metrics": "주요 성과 지표"
                    }},
                    "effectiveness_reasons": [
                        "구체적 효과성 이유1",
                        "구체적 효과성 이유2",
                        "구체적 효과성 이유3"
                    ],
                    "improvement_suggestions": [
                        "개선 제안1",
                        "개선 제안2"
                    ]
                }}
            ],
            "funnel_insights": {{
                "T1": {{
                    "common_patterns": ["T1 공통 패턴1", "T1 공통 패턴2"],
                    "success_factors": ["T1 성공 요인1", "T1 성공 요인2"],
                    "improvement_areas": ["T1 개선 영역1", "T1 개선 영역2"],
                    "recommendations": ["T1 추천사항1", "T1 추천사항2"]
                }},
                "T2": {{
                    "common_patterns": ["T2 공통 패턴1", "T2 공통 패턴2"],
                    "success_factors": ["T2 성공 요인1", "T2 성공 요인2"],
                    "improvement_areas": ["T2 개선 영역1", "T2 개선 영역2"],
                    "recommendations": ["T2 추천사항1", "T2 추천사항2"]
                }}
            }},
            "global_insights": {{
                "cross_funnel_patterns": ["전체 퍼널 공통 패턴1", "전체 퍼널 공통 패턴2"],
                "universal_success_factors": ["범용 성공 요인1", "범용 성공 요인2"],
                "funnel_specific_insights": {{
                    "early_funnel": ["초기 퍼널 인사이트1", "초기 퍼널 인사이트2"],
                    "mid_funnel": ["중간 퍼널 인사이트1", "중간 퍼널 인사이트2"],
                    "late_funnel": ["후기 퍼널 인사이트1", "후기 퍼널 인사이트2"]
                }},
                "conversion_optimization": {{
                    "high_conversion_funnels": ["고전환 퍼널1", "고전환 퍼널2"],
                    "low_conversion_funnels": ["저전환 퍼널1", "저전환 퍼널2"],
                    "optimization_priorities": ["최적화 우선순위1", "최적화 우선순위2"]
                }},
                "message_strategy": {{
                    "effective_keywords": ["효과적 키워드1", "효과적 키워드2"],
                    "effective_tones": ["효과적 톤1", "효과적 톤2"],
                    "avoid_patterns": ["피해야 할 패턴1", "피해야 할 패턴2"],
                    "recommended_approaches": ["추천 접근법1", "추천 접근법2"]
                }},
                "actionable_recommendations": [
                    "실행 가능한 추천사항1",
                    "실행 가능한 추천사항2",
                    "실행 가능한 추천사항3"
                ]
            }}
        }}
        """
        
        try:
            response = azure_llm.completion(
                model=f"azure/{settings.AZURE_OPENAI_DEPLOYMENT_NAME}",
                messages=[{"role": "user", "content": batch_prompt}],
                api_key=settings.AZURE_OPENAI_API_KEY,
                api_base=settings.AZURE_OPENAI_ENDPOINT,
                api_version=settings.AZURE_OPENAI_API_VERSION,
                temperature=0.3
            )
            
            response_text = response.choices[0].message.content
            
            # JSON 추출
            json_start = response_text.find('{')
            json_end = response_text.rfind('}') + 1
            
            if json_start != -1 and json_end != -1:
                json_str = response_text[json_start:json_end]
                batch_result = json.loads(json_str)
                
                print(f"✅ 전체 배치 분석 완료: {len(all_funnel_data)}개 문구, {len(funnel_stats)}개 퍼널 분석")
                
                return {
                    "status": "success",
                    "global_analysis": batch_result.get('global_analysis', {}),
                    "message_analyses": batch_result.get('message_analyses', []),
                    "funnel_insights": batch_result.get('funnel_insights', {}),
                    "global_insights": batch_result.get('global_insights', {}),
                    "funnel_stats": funnel_stats,
                    "analysis_type": "global_batch_with_accumulated_insights"
                }
            else:
                print("❌ JSON 파싱 실패, 기본값 사용")
                return {
                    "status": "error",
                    "error_message": "JSON 파싱 실패",
                    "funnel_stats": funnel_stats
                }
                
        except Exception as e:
            print(f"❌ 전체 배치 분석 중 오류: {str(e)}")
            return {
                "status": "error",
                "error_message": f"전체 배치 분석 중 오류: {str(e)}",
                "funnel_stats": funnel_stats
            }
        
    except Exception as e:
        return {
            "status": "error",
            "error_message": f"전체 배치 문구 효과성 분석 중 오류: {str(e)}"
        }

# def analyze_message_effectiveness_reasons_improved(df) -> Dict[str, Any]:
    """문구 효과성 이유 분석 (상위/하위 대조 분석 + 배치 처리 최적화)"""
    
    try:
        from sklearn.feature_extraction.text import TfidfVectorizer
        from sklearn.metrics.pairwise import cosine_similarity
        import numpy as np
        
        print("🔍 개선된 문구 효과성 이유 분석 시작 (상위/하위 대조 분석)...")
        
        effectiveness_analysis = {}
        
        # 퍼널별로 분석
        for funnel in df['퍼널'].unique():
            if pd.isna(funnel):
                continue
                
            print(f"\n📊 {funnel} 퍼널 대조 분석...")
            
            # 해당 퍼널의 데이터만 필터링
            funnel_data = df[df['퍼널'] == funnel]
            funnel_data_sorted = funnel_data.sort_values('실험군_예약전환율', ascending=False)
            
            # 상위 5개 + 하위 5개 문구 선택 (대조 분석)
            top_messages = funnel_data_sorted.head(5)
            bottom_messages = funnel_data_sorted.tail(5)
            
            if len(top_messages) < 2:
                continue
            
            # 퍼널별 평균 전환율 계산
            funnel_avg = funnel_data['실험군_예약전환율'].mean()
            
            # 상위/하위 문구 데이터 준비
            top_data = []
            bottom_data = []
            
            for i, (idx, row) in enumerate(top_messages.iterrows()):
                top_data.append({
                    "message": row['문구'],
                    "conversion_rate": row['실험군_예약전환율'],
                    "length": len(row['문구']),
                    "rank": i + 1,
                    "group": "high_performing"
                })
            
            for i, (idx, row) in enumerate(bottom_messages.iterrows()):
                bottom_data.append({
                    "message": row['문구'],
                    "conversion_rate": row['실험군_예약전환율'],
                    "length": len(row['문구']),
                    "rank": i + 1,
                    "group": "low_performing"
                })
            
            # 모든 문구 데이터 합치기
            all_message_data = top_data + bottom_data
            
            print(f"🚀 대조 분석 중: 상위 {len(top_data)}개 + 하위 {len(bottom_data)}개 = 총 {len(all_message_data)}개 문구 (API 호출 1회)")
            
            # 배치 프롬프트 생성
            batch_prompt = f"""
            다음 쏘카 CRM 문구들을 {funnel} 퍼널에서 대조 분석해주세요:
            
            퍼널: {funnel}
            퍼널 평균 전환율: {funnel_avg:.2f}%
            
            분석할 문구들 (상위/하위 대조):
            {json.dumps(all_message_data, ensure_ascii=False, indent=2)}
            
            각 문구에 대해 다음을 분석해주세요:
            
            1. **텍스트 구조적 특징** (수치 기반):
               - 문장 길이의 효과성 (평균 대비 분석)
               - 특수문자 사용의 효과
               - 숫자 사용의 효과
               - 문장 구조의 효과
            
            2. **심리적 어필 요소** (구체적 이유):
               - 감정적 자극 요소와 효과
               - 긴급성/제한성 어필의 효과
               - 혜택/할인 강조의 효과
            
            3. **퍼널별 적합성** (데이터 기반):
               - 퍼널 평균 대비 성과 분석
               - 고객 심리 상태와의 매칭도
               - 퍼널 단계별 특성과의 일치도
            
            4. **행동 유도 요소** (구체적 분석):
               - 명확한 행동 지시의 효과
               - 클릭 유도 문구의 효과
               - 다음 단계 안내의 효과
            
            5. **수치적 근거** (중요):
               - 전환율이 높은/낮은 구체적 이유
               - 다른 문구 대비 우수한/부족한 점
               - 성과 지표와 근거
            
            다음 JSON 형식으로 답변해주세요:
            {{
                "funnel_analysis": {{
                    "funnel": "{funnel}",
                    "funnel_avg_conversion": {funnel_avg:.2f},
                    "total_messages_analyzed": {len(all_message_data)},
                    "high_performing_count": {len(top_data)},
                    "low_performing_count": {len(bottom_data)}
                }},
                "message_analyses": [
                    {{
                        "message": "문구1",
                        "conversion_rate": 12.5,
                        "group": "high_performing",
                        "text_structure": {{
                            "length": 45,
                            "length_analysis": "문장 길이 45자의 효과성 분석",
                            "special_characters": "특수문자 사용 분석",
                            "numbers": "숫자 사용 분석",
                            "structure": "문장 구조 분석"
                        }},
                        "psychological_appeal": {{
                            "emotional_triggers": ["감정 자극 요소1", "감정 자극 요소2"],
                            "urgency": "긴급성 어필 정도",
                            "benefit_emphasis": "혜택 강조 정도"
                        }},
                        "funnel_fit": {{
                            "customer_state": "고객 심리 상태",
                            "message_alignment": "메시지 적합성",
                            "funnel_stage": "퍼널 단계별 특성",
                            "performance_vs_average": "평균 대비 성과"
                        }},
                        "action_induction": {{
                            "clear_instructions": "명확한 행동 지시",
                            "click_encouragement": "클릭 유도 요소",
                            "next_step_guidance": "다음 단계 안내"
                        }},
                        "numerical_evidence": {{
                            "conversion_rate": 12.5,
                            "performance_reason": "전환율 12.5%가 높은/낮은 구체적 이유",
                            "comparative_advantage": "다른 문구 대비 우수한/부족한 점",
                            "key_metrics": "주요 성과 지표"
                        }},
                        "effectiveness_reasons": [
                            "구체적 효과성 이유1",
                            "구체적 효과성 이유2",
                            "구체적 효과성 이유3"
                        ],
                        "improvement_suggestions": [
                            "개선 제안1",
                            "개선 제안2"
                        ]
                    }}
                ],
                "comparative_analysis": {{
                    "high_performing_patterns": ["고성과 문구 공통 패턴1", "고성과 문구 공통 패턴2"],
                    "low_performing_patterns": ["저성과 문구 공통 패턴1", "저성과 문구 공통 패턴2"],
                    "key_differences": ["주요 차이점1", "주요 차이점2"],
                    "success_factors": ["성공 요인1", "성공 요인2"],
                    "failure_factors": ["실패 요인1", "실패 요인2"],
                    "improvement_recommendations": ["개선 추천사항1", "개선 추천사항2"]
                }},
                "funnel_insights": {{
                    "common_patterns": ["공통 패턴1", "공통 패턴2"],
                    "success_factors": ["성공 요인1", "성공 요인2"],
                    "improvement_areas": ["개선 영역1", "개선 영역2"],
                    "recommendations": ["추천사항1", "추천사항2"]
                }}
            }}
            """
            
            try:
                response = azure_llm.completion(
                    model=f"azure/{settings.AZURE_OPENAI_DEPLOYMENT_NAME}",
                    messages=[{"role": "user", "content": batch_prompt}],
                    api_key=settings.AZURE_OPENAI_API_KEY,
                    api_base=settings.AZURE_OPENAI_ENDPOINT,
                    api_version=settings.AZURE_OPENAI_API_VERSION,
                    temperature=0.3
                )
                
                response_text = response.choices[0].message.content
                
                # JSON 추출
                json_start = response_text.find('{')
                json_end = response_text.rfind('}') + 1
                
                if json_start != -1 and json_end != -1:
                    json_str = response_text[json_start:json_end]
                    batch_result = json.loads(json_str)
                    
                    message_analyses = batch_result.get('message_analyses', [])
                    comparative_analysis = batch_result.get('comparative_analysis', {})
                    funnel_insights = batch_result.get('funnel_insights', {})
                    
                    print(f"✅ 대조 분석 완료: {len(message_analyses)}개 문구 분석")
                    
                    # 퍼널 인사이트를 결과에 추가
                    effectiveness_analysis[funnel] = {
                        "message_analyses": message_analyses,
                        "comparative_analysis": comparative_analysis,
                        "funnel_insights": funnel_insights,
                        "total_analyzed": len(message_analyses),
                        "funnel_avg_conversion": funnel_avg,
                        "high_performing_count": len(top_data),
                        "low_performing_count": len(bottom_data)
                    }
                else:
                    # JSON 파싱 실패시 기본값
                    print("❌ JSON 파싱 실패, 기본값 사용")
                    effectiveness_analysis[funnel] = {
                        "message_analyses": [],
                        "comparative_analysis": {},
                        "funnel_insights": {},
                        "total_analyzed": 0,
                        "funnel_avg_conversion": funnel_avg,
                        "high_performing_count": len(top_data),
                        "low_performing_count": len(bottom_data)
                    }
                    
            except Exception as e:
                print(f"❌ 대조 분석 중 오류: {str(e)}")
                effectiveness_analysis[funnel] = {
                    "message_analyses": [],
                    "comparative_analysis": {},
                    "funnel_insights": {},
                    "total_analyzed": 0,
                    "funnel_avg_conversion": funnel_avg,
                    "high_performing_count": len(top_data),
                    "low_performing_count": len(bottom_data)
                }
        
        return {
            "status": "success",
            "effectiveness_analysis": effectiveness_analysis,
            "total_funnels_analyzed": len(effectiveness_analysis),
            "analysis_type": "improved_batch_with_comparative_analysis"
        }
        
    except Exception as e:
        return {
            "status": "error",
            "error_message": f"개선된 문구 효과성 분석 중 오류: {str(e)}"
        }

# def analyze_message_effectiveness_reasons_batch(df) -> Dict[str, Any]:
    """문구 효과성 이유 분석 (배치 처리로 최적화)"""
    
    try:
        from sklearn.feature_extraction.text import TfidfVectorizer
        from sklearn.metrics.pairwise import cosine_similarity
        import numpy as np
        
        print("🔍 배치 문구 효과성 이유 분석 시작...")
        
        effectiveness_analysis = {}
        
        # 퍼널별로 분석
        for funnel in df['퍼널'].unique():
            if pd.isna(funnel):
                continue
                
            print(f"\n📊 {funnel} 퍼널 배치 문구 분석...")
            
            # 해당 퍼널의 데이터만 필터링
            funnel_data = df[df['퍼널'] == funnel]
            funnel_data_sorted = funnel_data.sort_values('실험군_예약전환율', ascending=False)
            
            # 상위 5개 문구 선택
            top_messages = funnel_data_sorted.head(5)
            
            if len(top_messages) < 2:
                continue
            
            # 퍼널별 평균 전환율 계산
            funnel_avg = funnel_data['실험군_예약전환율'].mean()
            
            # 문구 데이터 준비
            message_data = []
            for i, (idx, row) in enumerate(top_messages.iterrows()):
                message_data.append({
                    "message": row['문구'],
                    "conversion_rate": row['실험군_예약전환율'],
                    "length": len(row['문구']),
                    "rank": i + 1
                })
            
            print(f"🚀 배치 문구 분석 중: {len(message_data)}개 문구 (API 호출 1회)")
            
            # 배치 프롬프트 생성
            batch_prompt = f"""
            다음 쏘카 CRM 문구들을 {funnel} 퍼널에서 왜 효과적인지 구체적인 수치와 이유를 바탕으로 분석해주세요:
            
            퍼널: {funnel}
            퍼널 평균 전환율: {funnel_avg:.2f}%
            
            분석할 문구들:
            {json.dumps(message_data, ensure_ascii=False, indent=2)}
            
            각 문구에 대해 다음을 분석해주세요:
            
            1. **텍스트 구조적 특징** (수치 기반):
               - 문장 길이의 효과성 (평균 대비 분석)
               - 특수문자 사용의 효과
               - 숫자 사용의 효과
               - 문장 구조의 효과
            
            2. **심리적 어필 요소** (구체적 이유):
               - 감정적 자극 요소와 효과
               - 긴급성/제한성 어필의 효과
               - 혜택/할인 강조의 효과
            
            3. **퍼널별 적합성** (데이터 기반):
               - 퍼널 평균 대비 성과 분석
               - 고객 심리 상태와의 매칭도
               - 퍼널 단계별 특성과의 일치도
            
            4. **행동 유도 요소** (구체적 분석):
               - 명확한 행동 지시의 효과
               - 클릭 유도 문구의 효과
               - 다음 단계 안내의 효과
            
            5. **수치적 근거** (중요):
               - 전환율이 높은 구체적 이유
               - 다른 문구 대비 우수한 점
               - 성과 지표와 근거
            
            다음 JSON 형식으로 답변해주세요:
            {{
                "funnel_analysis": {{
                    "funnel": "{funnel}",
                    "funnel_avg_conversion": {funnel_avg:.2f},
                    "total_messages_analyzed": {len(message_data)}
                }},
                "message_analyses": [
                    {{
                        "message": "문구1",
                        "conversion_rate": 12.5,
                        "text_structure": {{
                            "length": 45,
                            "length_analysis": "문장 길이 45자의 효과성 분석",
                            "special_characters": "특수문자 사용 분석",
                            "numbers": "숫자 사용 분석",
                            "structure": "문장 구조 분석"
                        }},
                        "psychological_appeal": {{
                            "emotional_triggers": ["감정 자극 요소1", "감정 자극 요소2"],
                            "urgency": "긴급성 어필 정도",
                            "benefit_emphasis": "혜택 강조 정도"
                        }},
                        "funnel_fit": {{
                            "customer_state": "고객 심리 상태",
                            "message_alignment": "메시지 적합성",
                            "funnel_stage": "퍼널 단계별 특성",
                            "performance_vs_average": "평균 대비 성과"
                        }},
                        "action_induction": {{
                            "clear_instructions": "명확한 행동 지시",
                            "click_encouragement": "클릭 유도 요소",
                            "next_step_guidance": "다음 단계 안내"
                        }},
                        "numerical_evidence": {{
                            "conversion_rate": 12.5,
                            "performance_reason": "전환율 12.5%가 높은 구체적 이유",
                            "comparative_advantage": "다른 문구 대비 우수한 점",
                            "key_metrics": "주요 성과 지표"
                        }},
                        "effectiveness_reasons": [
                            "구체적 효과성 이유1",
                            "구체적 효과성 이유2",
                            "구체적 효과성 이유3"
                        ],
                        "improvement_suggestions": [
                            "개선 제안1",
                            "개선 제안2"
                        ]
                    }}
                ],
                "funnel_insights": {{
                    "common_patterns": ["공통 패턴1", "공통 패턴2"],
                    "success_factors": ["성공 요인1", "성공 요인2"],
                    "improvement_areas": ["개선 영역1", "개선 영역2"],
                    "recommendations": ["추천사항1", "추천사항2"]
                }}
            }}
            """
            
            try:
                response = azure_llm.completion(
                    model=f"azure/{settings.AZURE_OPENAI_DEPLOYMENT_NAME}",
                    messages=[{"role": "user", "content": batch_prompt}],
                    api_key=settings.AZURE_OPENAI_API_KEY,
                    api_base=settings.AZURE_OPENAI_ENDPOINT,
                    api_version=settings.AZURE_OPENAI_API_VERSION,
                    temperature=0.3
                )
                
                response_text = response.choices[0].message.content
                
                # JSON 추출
                json_start = response_text.find('{')
                json_end = response_text.rfind('}') + 1
                
                if json_start != -1 and json_end != -1:
                    json_str = response_text[json_start:json_end]
                    batch_result = json.loads(json_str)
                    
                    message_analyses = batch_result.get('message_analyses', [])
                    funnel_insights = batch_result.get('funnel_insights', {})
                    
                    print(f"✅ 배치 분석 완료: {len(message_analyses)}개 문구 분석")
                    
                    # 퍼널 인사이트를 결과에 추가
                    effectiveness_analysis[funnel] = {
                        "message_analyses": message_analyses,
                        "funnel_insights": funnel_insights,
                        "total_analyzed": len(message_analyses),
                        "funnel_avg_conversion": funnel_avg
                    }
                else:
                    # JSON 파싱 실패시 기본값
                    print("❌ JSON 파싱 실패, 기본값 사용")
                    effectiveness_analysis[funnel] = {
                        "message_analyses": [],
                        "funnel_insights": {},
                        "total_analyzed": 0,
                        "funnel_avg_conversion": funnel_avg
                    }
                    
            except Exception as e:
                print(f"❌ 배치 분석 중 오류: {str(e)}")
                effectiveness_analysis[funnel] = {
                    "message_analyses": [],
                    "funnel_insights": {},
                    "total_analyzed": 0,
                    "funnel_avg_conversion": funnel_avg
                }
        
        return {
            "status": "success",
            "effectiveness_analysis": effectiveness_analysis,
            "total_funnels_analyzed": len(effectiveness_analysis),
            "analysis_type": "batch_optimized"
        }
        
    except Exception as e:
        return {
            "status": "error",
            "error_message": f"배치 문구 효과성 분석 중 오류: {str(e)}"
        }

def analyze_message_effectiveness_reasons(df) -> Dict[str, Any]:
    """문구 효과성 이유 분석 (텍스트 유사도 + LLM 분석)"""
    
    try:
        from sklearn.feature_extraction.text import TfidfVectorizer
        from sklearn.metrics.pairwise import cosine_similarity
        import numpy as np
        
        print("🔍 문구 효과성 이유 분석 시작...")
        
        effectiveness_analysis = {}
        
        # 퍼널별로 분석
        for funnel in df['퍼널'].unique():
            if pd.isna(funnel):
                continue
                
            print(f"\n📊 {funnel} 퍼널 문구 효과성 이유 분석...")
            
            # 해당 퍼널의 데이터만 필터링
            funnel_data = df[df['퍼널'] == funnel]
            funnel_data_sorted = funnel_data.sort_values('실험군_예약전환율', ascending=False)
            
            # 상위 5개 문구 선택
            top_messages = funnel_data_sorted.head(5)
            
            if len(top_messages) < 2:
                continue
            
            # 1. 텍스트 유사도 분석
            messages = top_messages['문구'].fillna('').tolist()
            conversion_rates = top_messages['실험군_예약전환율'].tolist()
            
            # TF-IDF 벡터화
            vectorizer = TfidfVectorizer(max_features=100, stop_words=None)
            tfidf_matrix = vectorizer.fit_transform(messages)
            
            # 코사인 유사도 계산
            similarity_matrix = cosine_similarity(tfidf_matrix)
            
            # 2. LLM 기반 효과성 이유 분석
            effectiveness_reasons = []
            
            for i, (idx, row) in enumerate(top_messages.iterrows()):
                message = row['문구']
                conversion_rate = row['실험군_예약전환율']
                
                # LLM에게 효과성 이유 분석 요청 (수치와 구체적 이유 강화)
                prompt = f"""
                다음 쏘카 CRM 문구가 왜 효과적인지 구체적인 수치와 이유를 바탕으로 분석해주세요:
                
                **문구**: {message}
                **퍼널**: {funnel}
                **전환율**: {conversion_rate}%
                
                다음 관점에서 구체적으로 분석해주세요:
                
                1. **텍스트 구조적 특징** (수치 기반):
                   - 문장 길이: {len(message)}자 (평균 대비 분석)
                   - 특수문자 사용: 이모지, 기호 등 구체적 개수와 효과
                   - 숫자 사용: 구체적 수치와 그 효과
                   - 문장 구조: 단문/복문 비율과 효과
                
                2. **심리적 어필 요소** (구체적 이유):
                   - 감정적 자극 요소: 어떤 단어/표현이 왜 효과적인지
                   - 긴급성/제한성 어필: 구체적 표현과 그 효과
                   - 혜택/할인 강조: 수치와 표현 방식의 효과
                
                3. **퍼널별 적합성** (데이터 기반):
                   - 해당 퍼널의 평균 전환율 대비 이 문구의 성과
                   - 고객의 심리 상태와 메시지의 매칭도
                   - 퍼널 단계별 특성과의 일치도
                
                4. **행동 유도 요소** (구체적 분석):
                   - 명확한 행동 지시: 어떤 표현이 효과적인지
                   - 클릭 유도 문구: 구체적 문구와 효과
                   - 다음 단계 안내: 명확성과 효과
                
                5. **텍스트 유사도 기반 분석** (수치 포함):
                   - 다른 고성과 문구와의 공통점 (구체적 패턴)
                   - 차별화 요소 (구체적 차이점)
                   - 유사도 점수와 그 의미
                
                6. **수치적 근거** (중요):
                   - 전환율 {conversion_rate}%가 높은 이유
                   - 다른 문구 대비 우수한 점
                   - 구체적인 성과 지표와 근거
                
                JSON 형식으로 답변해주세요:
                {{
                    "text_structure": {{
                        "length": {len(message)},
                        "length_analysis": "문장 길이 {len(message)}자의 효과성 분석",
                        "special_characters": "특수문자 사용 분석 (구체적 개수와 효과)",
                        "numbers": "숫자 사용 분석 (구체적 수치와 효과)",
                        "structure": "문장 구조 분석 (단문/복문 비율과 효과)"
                    }},
                    "psychological_appeal": {{
                        "emotional_triggers": ["구체적 감정 자극 요소1", "구체적 감정 자극 요소2"],
                        "urgency": "긴급성 어필 정도와 구체적 표현",
                        "benefit_emphasis": "혜택 강조 정도와 구체적 수치"
                    }},
                    "funnel_fit": {{
                        "customer_state": "고객 심리 상태 분석",
                        "message_alignment": "메시지 적합성 (구체적 이유)",
                        "funnel_stage": "퍼널 단계별 특성과의 일치도",
                        "performance_vs_average": "평균 대비 성과 분석"
                    }},
                    "action_induction": {{
                        "clear_instructions": "명확한 행동 지시 (구체적 표현)",
                        "click_encouragement": "클릭 유도 요소 (구체적 문구)",
                        "next_step_guidance": "다음 단계 안내 (명확성 분석)"
                    }},
                    "similarity_analysis": {{
                        "common_patterns": ["구체적 공통 패턴1", "구체적 공통 패턴2"],
                        "differentiation": "차별화 요소 (구체적 차이점)",
                        "similarity_score": 0.85,
                        "similarity_meaning": "유사도 점수의 의미와 해석"
                    }},
                    "numerical_evidence": {{
                        "conversion_rate": {conversion_rate},
                        "performance_reason": "전환율 {conversion_rate}%가 높은 구체적 이유",
                        "comparative_advantage": "다른 문구 대비 우수한 점",
                        "key_metrics": "주요 성과 지표와 근거"
                    }},
                    "effectiveness_reasons": [
                        "구체적 효과성 이유1 (수치 포함)",
                        "구체적 효과성 이유2 (수치 포함)",
                        "구체적 효과성 이유3 (수치 포함)"
                    ],
                    "improvement_suggestions": [
                        "구체적 개선 제안1",
                        "구체적 개선 제안2"
                    ]
                }}
                """
                
                try:
                    response = azure_llm.completion(
                        model=f"azure/{settings.AZURE_OPENAI_DEPLOYMENT_NAME}",
                        messages=[{"role": "user", "content": prompt}],
                        api_key=settings.AZURE_OPENAI_API_KEY,
                        api_base=settings.AZURE_OPENAI_ENDPOINT,
                        api_version=settings.AZURE_OPENAI_API_VERSION,
                        temperature=0.3
                    )
                    
                    response_text = response.choices[0].message.content
                    
                    # JSON 추출
                    json_start = response_text.find('{')
                    json_end = response_text.rfind('}') + 1
                    
                    if json_start != -1 and json_end != -1:
                        json_str = response_text[json_start:json_end]
                        analysis_result = json.loads(json_str)
                        
                        # 유사도 점수 추가
                        if i < len(similarity_matrix):
                            avg_similarity = np.mean([similarity_matrix[i][j] for j in range(len(similarity_matrix)) if i != j])
                            analysis_result['similarity_analysis']['similarity_score'] = float(avg_similarity)
                        
                        effectiveness_reasons.append({
                            'message': message,
                            'conversion_rate': conversion_rate,
                            'analysis': analysis_result
                        })
                        
                except Exception as e:
                    print(f"문구 {i+1} 분석 실패: {e}")
                    continue
            
            # 3. 퍼널별 종합 분석
            if effectiveness_reasons:
                # 공통 패턴 추출
                all_patterns = []
                for reason in effectiveness_reasons:
                    patterns = reason['analysis'].get('similarity_analysis', {}).get('common_patterns', [])
                    all_patterns.extend(patterns)
                
                pattern_counts = Counter(all_patterns)
                top_patterns = pattern_counts.most_common(5)
                
                # 공통 효과성 이유 추출
                all_reasons = []
                for reason in effectiveness_reasons:
                    reasons = reason['analysis'].get('effectiveness_reasons', [])
                    all_reasons.extend(reasons)
                
                reason_counts = Counter(all_reasons)
                top_reasons = reason_counts.most_common(5)
                
                effectiveness_analysis[funnel] = {
                    'total_messages_analyzed': len(effectiveness_reasons),
                    'top_patterns': top_patterns,
                    'top_effectiveness_reasons': top_reasons,
                    'detailed_analyses': effectiveness_reasons,
                    'avg_similarity_score': np.mean([r['analysis']['similarity_analysis']['similarity_score'] for r in effectiveness_reasons])
                }
        
        return {
            "status": "success",
            "effectiveness_analysis": effectiveness_analysis,
            "message": "문구 효과성 이유 분석 완료"
        }
        
    except Exception as e:
        return {"status": "error", "error_message": str(e)}

