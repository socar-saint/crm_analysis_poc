"""Comprehensive Agent - 모든 분석을 통합하는 종합 분석 Agent"""

import pandas as pd
import json
import asyncio
from typing import Dict, Any, List
from google.adk.agents import Agent
from google.adk.models.lite_llm import LiteLlm
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types

from settings import get_logger, settings
from analysis_context import analysis_context
from data_analysis_functions import (
    analyze_conversion_performance,
    analyze_message_effectiveness,
    analyze_funnel_performance,
    analyze_funnel_message_effectiveness,
    analyze_message_patterns_by_funnel,
    analyze_single_message_llm,
    analyze_messages_by_funnel_llm,
    analyze_message_effectiveness_reasons
)
from column_descriptions import SIMPLE_COLUMN_DESCRIPTIONS

logger = get_logger(__name__)

# Azure OpenAI 설정
azure_llm = LiteLlm(
    model=f"azure/{settings.AZURE_OPENAI_DEPLOYMENT_NAME}",
    api_key=settings.AZURE_OPENAI_API_KEY,
    api_base=settings.AZURE_OPENAI_ENDPOINT,
    api_version=settings.AZURE_OPENAI_API_VERSION,
)

# =============================================================================
# 통합 분석 도구들
# =============================================================================

def comprehensive_data_analysis(csv_file_path: str) -> str:
    """종합 데이터 분석 수행"""
    try:
        print("🔍 종합 데이터 분석 시작...")
        
        # 데이터 로드
        df = pd.read_csv(csv_file_path)
        
        # 1. 데이터 이해도 분석
        data_understanding = {
            "data_shape": df.shape,
            "columns": df.columns.tolist(),
            "missing_values": df.isnull().sum().to_dict(),
            "data_types": df.dtypes.to_dict(),
            "basic_stats": df.describe().to_dict()
        }
        analysis_context.update_data_understanding(data_understanding)
        
        # 2. 통계 분석
        statistical_results = {
            "conversion_analysis": analyze_conversion_performance(df),
            "message_analysis": analyze_message_effectiveness(df),
            "funnel_analysis": analyze_funnel_performance(df),
            "funnel_message_analysis": analyze_funnel_message_effectiveness(df),
            "pattern_analysis": analyze_message_patterns_by_funnel(df)
        }
        analysis_context.update_statistical_analysis(statistical_results)
        
        # 3. LLM 분석
        llm_results = {
            "message_llm_analysis": analyze_messages_by_funnel_llm(df, sample_size=3),
            "effectiveness_reasons": analyze_message_effectiveness_reasons(df)
        }
        analysis_context.update_llm_analysis(llm_results)
        
        # 4. 통합 인사이트 생성
        integrated_insights = analysis_context.integrate_insights()
        
        return f"종합 분석 완료: {len(integrated_insights)}개 통합 인사이트 생성"
        
    except Exception as e:
        return f"종합 분석 오류: {str(e)}"

def generate_insights_report(csv_file_path: str) -> str:
    """인사이트 보고서 생성"""
    try:
        print("📊 인사이트 보고서 생성 중...")
        
        # 통합 인사이트 생성
        integrated_insights = analysis_context.integrate_insights()
        
        # 최종 보고서 생성
        final_report = analysis_context.generate_final_report()
        
        # JSON 저장
        analysis_context.save_to_json("comprehensive_analysis_report.json")
        
        # DataFrame 저장
        analysis_context.save_to_dataframe("comprehensive_analysis_results.csv")
        
        return f"인사이트 보고서 생성 완료: {len(final_report)}개 섹션"
        
    except Exception as e:
        return f"인사이트 보고서 생성 오류: {str(e)}"

def analyze_specific_funnel(csv_file_path: str, funnel_name: str) -> str:
    """특정 퍼널 상세 분석"""
    try:
        df = pd.read_csv(csv_file_path)
        funnel_data = df[df['퍼널'] == funnel_name]
        
        if len(funnel_data) == 0:
            return f"퍼널 '{funnel_name}' 데이터가 없습니다."
        
        # 퍼널별 상세 분석
        funnel_analysis = {
            "funnel_name": funnel_name,
            "total_campaigns": len(funnel_data),
            "avg_conversion_rate": funnel_data['실험군_예약전환율'].mean(),
            "best_message": funnel_data.loc[funnel_data['실험군_예약전환율'].idxmax(), '문구'],
            "best_conversion_rate": funnel_data['실험군_예약전환율'].max(),
            "channel_distribution": funnel_data['채널'].value_counts().to_dict()
        }
        
        # Context에 추가
        analysis_context.update_statistical_analysis({f"funnel_{funnel_name}": funnel_analysis})
        
        return f"퍼널 '{funnel_name}' 분석 완료: {funnel_analysis['total_campaigns']}개 캠페인"
        
    except Exception as e:
        return f"퍼널 분석 오류: {str(e)}"

def compare_experiment_vs_control(csv_file_path: str) -> str:
    """실험군 vs 대조군 상세 비교"""
    try:
        df = pd.read_csv(csv_file_path)
        
        # 실험군 vs 대조군 비교
        comparison = {
            "experiment_avg_conversion": df['실험군_예약전환율'].mean(),
            "control_avg_conversion": df['대조군_예약전환율'].mean(),
            "lift_percentage": df['실험군_예약전환율'].mean() - df['대조군_예약전환율'].mean(),
            "statistical_significance": "분석 필요",
            "best_performing_campaigns": df.nlargest(5, '실험군_예약전환율')[['퍼널', '문구', '실험군_예약전환율']].to_dict('records')
        }
        
        # Context에 추가
        analysis_context.update_statistical_analysis({"experiment_control_comparison": comparison})
        
        return f"실험군 vs 대조군 비교 완료: Lift {comparison['lift_percentage']:.2f}%"
        
    except Exception as e:
        return f"실험군 vs 대조군 비교 오류: {str(e)}"

def generate_actionable_recommendations(csv_file_path: str) -> str:
    """실행 가능한 추천사항 생성"""
    try:
        print("💡 실행 가능한 추천사항 생성 중...")
        
        df = pd.read_csv(csv_file_path)
        
        # 데이터 기반 추천사항 생성
        recommendations = []
        
        # 1. 퍼널별 추천
        funnel_performance = df.groupby('퍼널')['실험군_예약전환율'].agg(['mean', 'count']).round(3)
        best_funnel = funnel_performance['mean'].idxmax()
        worst_funnel = funnel_performance['mean'].idxmin()
        
        recommendations.append({
            "category": "퍼널 최적화",
            "priority": "high",
            "recommendation": f"'{best_funnel}' 퍼널의 성공 패턴을 '{worst_funnel}' 퍼널에 적용",
            "expected_impact": f"전환율 {funnel_performance.loc[worst_funnel, 'mean']:.1f}% → {funnel_performance.loc[best_funnel, 'mean']:.1f}% 개선 가능"
        })
        
        # 2. 문구별 추천
        message_performance = df.groupby('문구')['실험군_예약전환율'].agg(['mean', 'count']).round(3)
        best_message = message_performance['mean'].idxmax()
        
        recommendations.append({
            "category": "메시지 최적화",
            "priority": "high",
            "recommendation": f"고성과 문구 패턴 분석 및 적용",
            "best_message_sample": best_message[:100] + "...",
            "conversion_rate": f"{message_performance.loc[best_message, 'mean']:.1f}%"
        })
        
        # 3. 채널별 추천
        channel_performance = df.groupby('채널')['실험군_예약전환율'].agg(['mean', 'count']).round(3)
        best_channel = channel_performance['mean'].idxmax()
        
        recommendations.append({
            "category": "채널 최적화",
            "priority": "medium",
            "recommendation": f"'{best_channel}' 채널의 성공 요소를 다른 채널에 적용",
            "channel_performance": channel_performance.to_dict()
        })
        
        # Context에 추가
        analysis_context.update_statistical_analysis({"actionable_recommendations": recommendations})
        
        return f"실행 가능한 추천사항 {len(recommendations)}개 생성 완료"
        
    except Exception as e:
        return f"추천사항 생성 오류: {str(e)}"

# =============================================================================
# Comprehensive Agent 생성
# =============================================================================

comprehensive_agent = Agent(
    name="comprehensive_agent",
    model=azure_llm,
    description="CRM 데이터의 종합 분석을 수행하고 통합 인사이트를 제공하는 전문가입니다.",
    instruction=f"""
    # 종합 CRM 분석 전문가
    
    ## 역할
    당신은 쏘카의 Senior Data Analyst로서, CRM 캠페인 데이터를 종합적으로 분석하여 
    비즈니스 인사이트와 실행 가능한 추천사항을 제공하는 전문가입니다.
    
    ## 컬럼 설명
    {SIMPLE_COLUMN_DESCRIPTIONS}
    
    ## 분석 목표
    1. 데이터 이해도 및 품질 분석
    2. 통계적 성과 분석 (전환율, 퍼널별, 채널별)
    3. LLM 기반 문구 효과성 분석
    4. 실험군 vs 대조군 비교 분석
    5. 통합 인사이트 및 추천사항 도출
    
    ## 출력 형식
    - 종합 분석 결과 요약
    - 통계적 지표 및 성과 분석
    - 문구 효과성 및 패턴 분석
    - 실행 가능한 비즈니스 추천사항
    - DataFrame/JSON 형태의 구조화된 결과
    
    ## Context 공유
    - 모든 분석 결과는 Context에 저장되어 후속 분석에서 활용
    - 이전 분석 결과를 참조하여 더 정확한 인사이트 도출
    - 통합된 관점에서 종합적인 분석 수행
    """,
    tools=[
        comprehensive_data_analysis,
        generate_insights_report,
        analyze_specific_funnel,
        compare_experiment_vs_control,
        generate_actionable_recommendations
    ],
)

# =============================================================================
# 실행 함수
# =============================================================================

async def run_agent_with_llm(agent, query: str, agent_name: str):
    """LLM Agent 실행"""
    user_id = "comprehensive_user"
    session_id = f"session_{agent_name}"

    # 세션 서비스 생성
    session_service = InMemorySessionService()

    # Runner 생성
    runner = Runner(
        agent=agent,
        session_service=session_service,
        app_name=f"{agent_name}_app"
    )

    # 세션 생성
    await session_service.create_session(
        app_name=f"{agent_name}_app",
        user_id=user_id,
        session_id=session_id
    )

    print(f"🤖 {agent_name} Agent 실행 중...")

    content = types.Content(role="user", parts=[types.Part(text=query)])

    async for event in runner.run_async(user_id=user_id, session_id=session_id, new_message=content):
        if event.is_final_response():
            if event.content and event.content.parts:
                response = event.content.parts[0].text
                print(f"📝 {agent_name} 응답: {response}")
            break

async def run_comprehensive_analysis():
    """종합 분석 시스템 실행"""
    print("🚀 종합 분석 시스템 시작")
    print("=" * 80)

    # CSV 파일 경로
    csv_file = "clean_df_renamed.csv"

    # 종합 분석 쿼리
    comprehensive_query = f"""
    다음 CRM 데이터를 종합적으로 분석해주세요: {csv_file}

    다음 단계를 따라 종합 분석을 수행해주세요:
    
    1. **데이터 이해도 분석**
       - 데이터 구조, 품질, 기본 통계 분석
       - 컬럼별 특성 및 결측치 분석
    
    2. **통계적 성과 분석**
       - 실험군 vs 대조군 전환율 비교
       - 퍼널별 성과 분석
       - 채널별 성과 분석
       - 문구별 효과성 분석
    
    3. **LLM 기반 문구 분석**
       - 문구 구조 및 패턴 분석
       - 톤앤매너 및 키워드 분석
       - 효과성 이유 분석
    
    4. **통합 인사이트 도출**
       - 모든 분석 결과를 종합한 인사이트
       - 교차 분석을 통한 새로운 발견
       - 비즈니스 임팩트 평가
    
    5. **실행 가능한 추천사항**
       - 퍼널 최적화 방안
       - 메시지 개선 제안
       - 채널 전략 수정
       - 우선순위별 액션 아이템
    
    6. **결과 보고서 생성**
       - JSON 형태의 구조화된 결과
       - DataFrame 형태의 정량적 결과
       - 경영진 요약 보고서
    
    각 단계마다 도구를 사용해서 실제 분석을 수행하고, 
    모든 결과를 Context에 저장하여 통합적인 관점에서 분석해주세요.
    """

    await run_agent_with_llm(comprehensive_agent, comprehensive_query, "comprehensive_analysis")

    print("\n✅ 종합 분석 시스템 완료!")
    print("=" * 80)

if __name__ == "__main__":
    asyncio.run(run_comprehensive_analysis())
