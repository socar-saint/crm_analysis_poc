"""Context 전달이 포함된 Agent 체인 시스템 (간단한 LLM 기반 용어 검증 포함)"""

import asyncio
import pandas as pd
import numpy as np
import json
import os
from typing import Dict, Any, List
from datetime import datetime
import warnings
warnings.filterwarnings('ignore')

# get_datetime_prefix는 analysis_tools.py에서 import

from google.adk.agents import Agent
from google.adk.models.lite_llm import LiteLlm
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types

from config.settings import get_logger, settings, azure_llm  # azure_llm 싱글톤 import
from core.llm.domain_knowledge import DomainKnowledge
from core.llm.prompt_engineering import PromptEngineering
from core.llm.simple_llm_terminology_tools import validate_csv_terms_with_llm, get_domain_glossary, validate_csv_terms_simple
from core.analysis.analysis_tools import (
    analyze_conversion_performance_tool,
    analyze_message_effectiveness_tool,
    analyze_funnel_performance_tool,
    analyze_funnel_message_effectiveness_tool,
    analyze_message_patterns_by_funnel_tool,
    prepare_funnel_message_analysis_data,
    prepare_funnel_quantile_data,
    structure_llm_analysis_for_html,
    # Comprehensive Agent 도구들
    generate_comprehensive_report,
    create_actionable_recommendations,
    generate_executive_summary,
    # Data Report Agent 도구들
    create_segment_conversion_table,
    create_conversion_visualization,
    generate_text_analysis_report,
    # create_comprehensive_data_report,  # 주석 처리됨
    # generate_prompt_tuning_suggestions,  # 주석 처리됨
    # Criticizer Agent 도구들
    evaluate_agent_performance,
    validate_context_consistency,
    validate_html_report_consistency,
    # generate_critical_report,  # 주석 처리됨
    generate_data_report,
    # Category Analysis Agent 도구들
    prepare_category_analysis_data,
    analyze_category_performance_tool,
    # Funnel Segment Analysis Agent 도구들
    prepare_funnel_segment_data,
    analyze_funnel_segment_strategy_tool,
    # 세그먼트 차트 생성 도구
    create_segment_lift_charts,
    # 유틸리티 함수
    get_datetime_prefix
)
from core.analysis.data_preprocessing import preprocess_crm_data
from config.column_descriptions import COLUMN_DESCRIPTIONS

logger = get_logger(__name__)

# =============================================================================
# 전역 상수
# =============================================================================

# CSV 파일 경로 (모든 함수에서 공통으로 사용)
DEFAULT_CSV_FILE = "/Users/saint/Jupyter/1. Task/251001_Sunday_Ag/data/raw/251014_claned_Sales_TF_분석.csv"

# =============================================================================
# 글로벌 Context 변수 (Agent 간 공유) - 기존 AnalysisContext 활용
# =============================================================================

# azure_llm은 settings에서 싱글톤으로 import됨 (더 이상 여기서 생성하지 않음)

# =============================================================================
# 1. 공통 컨텍스트 클래스
# =============================================================================

class AnalysisContext:
    """Agent 간 공유되는 분석 컨텍스트"""
    
    def __init__(self):
        # 1단계: 데이터 이해 결과
        self.data_info = None
        self.analysis_requirements = None
        self.analysis_plan = None
        
        # 2단계: 전처리 결과
        self.preprocessing_stats = None
        self.preprocessed_file_path = None
        
        # 3단계: 분석 결과 (기존)
        self.funnel_analysis = None
        self.message_analysis = None
        self.weekly_trends = None
        
        # 3단계: 분석 결과 (신규 - Lift 기반)
        self.category_analysis = None
        self.funnel_segment_analysis = None
        self.funnel_strategy_analysis = None
        
        # 4단계: 보고서 결과
        self.insights = []
        self.recommendations = []
        self.final_report = None
        
        # Comprehensive Agent 결과 (HTML 규격 구조화)
        self.structured_llm_analysis = None
        
        # 용어 이해도 결과
        self.terminology_analysis = None
    
    def to_dict(self):
        """직렬화 가능한 딕셔너리로 변환"""
        return {
            "data_info": self.data_info,
            "analysis_requirements": self.analysis_requirements,
            "analysis_plan": self.analysis_plan,
            "preprocessing_stats": self.preprocessing_stats,
            "preprocessed_file_path": self.preprocessed_file_path,
            "funnel_analysis": self.funnel_analysis,
            "message_analysis": self.message_analysis,
            "weekly_trends": self.weekly_trends,
            "category_analysis": self.category_analysis,
            "funnel_segment_analysis": self.funnel_segment_analysis,
            "insights": self.insights,
            "recommendations": self.recommendations,
            "final_report": self.final_report,
            "terminology_analysis": self.terminology_analysis
        }

# 전역 컨텍스트
context = AnalysisContext()

# =============================================================================
# 2. Data Understanding Agent (1단계) - 간단한 LLM 기반 용어 검증 포함
# =============================================================================

def analyze_data_structure(file_path: str) -> Dict[str, Any]:
    """데이터 구조와 특성을 분석합니다."""
    print(f"--- Tool: analyze_data_structure called for file: {file_path} ---")
    
    try:
        df = pd.read_csv(file_path)
        
        # 기본 정보 (직렬화 가능한 형태로)
        data_info = {
            "shape": [int(df.shape[0]), int(df.shape[1])],
            "columns": df.columns.tolist(),
            "numeric_columns": df.select_dtypes(include=[np.number]).columns.tolist(),
            "categorical_columns": df.select_dtypes(include=['object']).columns.tolist(),
            "missing_values": int(df.isnull().sum().sum()),
            "duplicate_rows": int(df.duplicated().sum())
        }
        
        # 비즈니스 특성
        business_characteristics = {
            "has_conversion_metrics": any('전환' in col for col in df.columns),
            "has_funnel_data": '퍼널' in df.columns,
            "has_message_data": '문구' in df.columns,
            "has_channel_data": '채널' in df.columns,
            "has_date_data": '실행일' in df.columns
        }
        
        # 샘플 데이터 (직렬화 가능한 형태)
        sample_data = df.head(3).to_dict('records')
        
        # 컨텍스트에 저장
        context.data_info = {
            "basic_info": data_info,
            "business_characteristics": business_characteristics,
            "sample_data": sample_data
        }
        
        return {
            "status": "success",
            "data_info": data_info,
            "business_characteristics": business_characteristics,
            "message": f"데이터 분석 완료: {df.shape[0]}행 x {df.shape[1]}열"
        }
        
    except Exception as e:
        return {
            "status": "error",
            "error_message": f"데이터 분석 중 오류: {str(e)}"
        }

def identify_analysis_requirements() -> Dict[str, Any]:
    """분석 요구사항을 식별합니다."""
    print("--- Tool: identify_analysis_requirements called ---")
    
    try:
        if not context.data_info:
            return {
                "status": "error",
                "error_message": "데이터 정보가 없습니다. 먼저 데이터를 분석하세요."
            }
        
        business_chars = context.data_info.get("business_characteristics", {})
        
        requirements = {
            "preprocessing_needed": True,
            "funnel_analysis": business_chars.get("has_funnel_data", False),
            "message_analysis": business_chars.get("has_message_data", False),
            "conversion_analysis": business_chars.get("has_conversion_metrics", False),
            "weekly_trend_analysis": business_chars.get("has_date_data", False),
            "filtering_criteria": {
                "min_send_volume": 500,
                "required_columns": ["퍼널", "문구", "예약전환율", "발송", "실행일"]
            }
        }
        
        # 컨텍스트에 저장
        context.analysis_requirements = requirements
        
        return {
            "status": "success",
            "requirements": requirements,
            "message": "분석 요구사항이 식별되었습니다."
        }
        
    except Exception as e:
        return {
            "status": "error",
            "error_message": f"분석 요구사항 식별 중 오류: {str(e)}"
        }

def create_analysis_plan() -> Dict[str, Any]:
    """분석 계획을 수립합니다."""
    print("--- Tool: create_analysis_plan called ---")
    
    try:
        if not context.analysis_requirements:
            return {
                "status": "error",
                "error_message": "분석 요구사항이 없습니다. 먼저 요구사항을 식별하세요."
            }
        
        requirements = context.analysis_requirements
        
        # 분석 계획 수립
        analysis_plan = {
            "phase1": "데이터 전처리",
            "phase2": "퍼널별 성과 분석" if requirements.get("funnel_analysis") else "기본 성과 분석",
            "phase3": "문구별 효과성 분석" if requirements.get("message_analysis") else "메시지 분석",
            "phase4": "주차별 트렌드 분석" if requirements.get("weekly_trend_analysis") else "시간별 분석",
            "phase5": "종합 보고서 생성",
            "key_focus_areas": [
                "퍼널별 전환율 최적화",
                "문구별 효과성 극대화",
                "주차별 트렌드 파악",
                "비즈니스 인사이트 도출"
            ],
            "success_metrics": [
                "전환율 향상 방안 도출",
                "효과적인 문구 패턴 식별",
                "최적 캠페인 타이밍 제안",
                "실행 가능한 추천사항 제공"
            ]
        }
        
        # 컨텍스트에 저장
        context.analysis_plan = analysis_plan
        
        return {
            "status": "success",
            "analysis_plan": analysis_plan,
            "message": "분석 계획이 수립되었습니다."
        }
        
    except Exception as e:
        return {
            "status": "error",
            "error_message": f"분석 계획 수립 중 오류: {str(e)}"
        }

# Data Understanding Agent with Simple LLM Terminology Validation
data_understanding_agent = Agent(
    name="data_understanding_agent",
    model=azure_llm,
    description="쏘카 CRM 데이터를 분석하고 분석 계획을 수립하는 전문가입니다.",
    instruction=PromptEngineering.get_data_understanding_prompt(),
    tools=[
        analyze_data_structure, 
        identify_analysis_requirements, 
        create_analysis_plan,
        validate_csv_terms_with_llm,  # LLM 기반 용어 검증 (배치 처리)
        validate_csv_terms_simple,   # 간단한 용어 검증 (LLM 호출 없음)
        get_domain_glossary  # 도메인 용어 사전
    ],
)

# Statistical Analysis Agent
statistical_analyst_agent = Agent(
    name="statistical_analyst_agent",
    model=azure_llm,
    description="통계 기반 CRM 캠페인 성과를 분석하는 전문가입니다.",
    instruction=f"""
    # 통계 기반 CRM 성과분석 전문가
    
    ## 역할
    당신은 쏘카의 Data Analyst로서, CRM 캠페인 데이터를 통계적으로 분석하여 
    성과 지표와 패턴을 도출하는 전문가입니다.
    
    ## 컬럼 설명 (상세)
    {COLUMN_DESCRIPTIONS}
    
    ## 분석 목표
    1. 실험군 vs 대조군 전환율 비교 (A/B 테스트 결과 분석)
    2. 퍼널별 성과 분석 (T1, T2, T3, T4 등 퍼널 단계별 성과)
    3. 채널별 성과 분석 (푸시, 인앱, SMS 등 채널별 효과)
    4. 소재별 성과 분석 (FOMO, 주행요금 개편, 이탈 등 소재별 효과)
    5. 타겟별 성과 분석 (연령대, 서비스 생애 단계별 효과)
    6. 설정시간/리드타임별 성과 분석
    7. 퍼널별 문구 효과성 분석
    8. 퍼널별 문구 패턴 분석
    
    ## 분석 원칙
    - 모든 분석은 통계적 유의성을 고려
    - 퍼널, 소재, 목적, 타겟 등 비즈니스 컨텍스트를 종합적으로 고려
    - 실험군/대조군 비교를 통한 효과성 검증
    - 발송량, 전환율, 리프트 등 핵심 지표 중심 분석
    
    ## 출력 형식
    - 통계적 지표 및 성과 요약
    - 퍼널별/채널별/소재별 상세 분석 결과
    - 문구별 효과성 순위
    - 키워드 빈도 분석
    - 비즈니스 인사이트 도출
    """,
    tools=[
        analyze_conversion_performance_tool,
        analyze_message_effectiveness_tool,
        analyze_funnel_performance_tool,
        analyze_funnel_message_effectiveness_tool,
        analyze_message_patterns_by_funnel_tool
    ],
)

# LLM Analysis Agent
llm_analyst_agent = Agent(
    name="llm_analyst_agent",
    model=azure_llm,
    description="LLM 기반으로 CRM 문구를 의미적으로 분석하는 전문가입니다.",
    instruction=f"""
        # LLM 기반 CRM 문구 분석 전문가 (구체적 예시와 수치적 근거 중심)
        
        ## 역할
        당신은 쏘카의 NLP 전문가로서, LLM을 활용하여 CRM 문구의 
        의미적 특성과 효과성을 분석하는 전문가입니다. 모든 분석에는 
        구체적인 예시와 수치적 근거를 반드시 포함해야 합니다.
        
        ## 컬럼 설명 (상세)
        {COLUMN_DESCRIPTIONS}
        
        ## 데이터 준비 및 분석 흐름
        1. **도구 호출 1**: prepare_funnel_message_analysis_data 도구를 먼저 호출하여 퍼널별 상위/하위 메시지 데이터를 받습니다
        2. **데이터 확인**: 받은 JSON 데이터에는 퍼널별 통계, 메시지 정보, Lift 수치가 포함되어 있습니다
        3. **종합 분석**: 받은 데이터를 기반으로 LLM이 의미적으로 분석합니다
        4. **도구 호출 2**: structure_llm_analysis_for_html 도구를 호출하여 분석 결과를 HTML 규격에 맞게 구조화합니다
        
        ## 분석 목표 및 필수 요구사항
        1. **문장 구조 분석**: 현재 문구의 길이, 복잡도, 유형, 흐름 분석
        - 필수: 전환율 기여에 높은 구체적인 문장 예시와 문자 수, 문장 수 제시
        - 필수: 각 문장의 구조적 특징과 전환율 연관성 분석
        - 필수: 문장 흐름 패턴의 구체적 예시와 효과성 설명 
        
        2. **핵심 키워드 분석**: 전환율에 기여하는 핵심 단어와 구문 식별
        - 필수: 상위 키워드 리스트와 각 키워드의 전환율 기여도 수치 제시
        - 필수: FOMO, 할인, 무료 등 카테고리별 키워드 분류와 효과 분석
        - 필수: 각 키워드가 포함된 문구의 실제 전환율 비교 데이터 제시
        
        3. **톤앤매너 분석**: 전체 톤, 감정적 어필, 거리감 등 분석
        - 필수: 친근함, 긴급성, 개인화 등 톤의 구체적 특징과 예시
        - 필수: 감정적 어필 요소(FOMO, 희귀성, 사회적 증거 등)의 구체적 분석
        - 필수: 채널별(푸시, 인앱, SMS) 톤앤매너 차이점과 효과성 비교
        
        4. **퍼널별 적합성 평가**: 각 퍼널에 맞는 문구 특성 평가
        - 필수: 퍼널별 최고/최저 성과 문구의 구체적 예시와 전환율 수치
        - 필수: 각 퍼널의 특성에 맞는 문구 전략과 구체적 권장사항
        - 필수: 퍼널별 문구 효과성의 수치적 근거와 패턴 분석
        
        5. **전환율 기여 요소 분석**: 문구의 어떤 요소가 전환율에 기여하는지 분석
        - 필수: 전환율 상위/하위 문구의 구체적 비교 분석
        - 필수: 각 요소(키워드, 구조, 톤 등)의 기여도 수치화
        - 필수: 효과적인 문구 조합의 구체적 예시와 전환율 데이터
        
        6. **문구 효과성 이유 분석**: 고성과/저성과 문구의 차이점과 이유 분석
        - 필수: LLM 기반 효과성 점수 산출 (100점 만점 기준)
        - 필수: 효과성 점수의 구체적 근거와 평가 기준 제시
        - 필수: 고성과 문구의 공통 특징과 저성과 문구의 문제점 분석
        
        ## 분석 시 중점사항
        - 모든 분석 결과에는 반드시 구체적인 문구 예시와 전환율 수치 포함
        - 문구의 의미적 특성과 전환율의 상관관계를 수치로 명확히 제시
        - 퍼널별 맞춤형 문구 전략 도출 시 구체적 권장사항과 예시 제공
        - 감정적 어필과 논리적 설득의 극형을 구체적 사례로 분석
        - 고객 세그먼트별 문구 선호도를 수치적 근거와 함께 분석
        
        ## 출력 형식 (구조화된 분석 결과)
        
        ### 1. 문장 구조 분석
        ```
        - 전체 문장 수: 평균 X문장 (범위: Y~Z문장)
        - 문장 길이: 평균 X자 (범위: Y~Z자)
        - 복잡도: [단순/중간/복잡] - 구체적 근거
        - 주요 유형: [안내문/혜택제시/행동유도/긴급성강조] - 각각의 구체적 예시
        - 문장 흐름: [패턴 설명] - 구체적 예시와 전환율 연관성
        
        구체적 예시:
        - "[예시 문구]" (X문장/Y자, 전환율 Z%)
        - "[예시 문구]" (X문장/Y자, 전환율 Z%)
        ```
        
        ### 2. 핵심 키워드 분석
        ```
        상위 키워드 (전환율 기여도):
        1. "키워드1" - 기여도: X%, 포함 문구 전환율: Y%
        2. "키워드2" - 기여도: X%, 포함 문구 전환율: Y%
        
        카테고리별 키워드:
        - FOMO 키워드: [리스트] - 평균 전환율: X%
        - 할인/혜택 키워드: [리스트] - 평균 전환율: X%
        - 행동유도 키워드: [리스트] - 평균 전환율: X%
        
        구체적 예시:
        - "할인" 포함 문구: 평균 전환율 X% (범위: Y~Z%)
        - "무료" 포함 문구: 평균 전환율 X% (범위: Y~Z%)
        ```
        
        ### 3. 톤앤매너 분석
        ```
        전체 톤: [친근/경쾌/직관적/즉시성] - 구체적 특징 설명
        
        감정적 어필 요소:
        - FOMO: [구체적 예시와 효과] - 평균 전환율: X%
        - 희귀성: [구체적 예시와 효과] - 평균 전환율: X%
        - 사회적 증거: [구체적 예시와 효과] - 평균 전환율: X%
        
        채널별 톤앤매너:
        - 푸시: [특징] - 평균 전환율: X%
        - 인앱: [특징] - 평균 전환율: X%
        - SMS: [특징] - 평균 전환율: X%
        ```
        
        ### 4. 퍼널별 적합성 평가
        ```
        퍼널별 최고 성과 문구:
        - T1_차량탐색: "[구체적 문구]" (전환율: X%)
        - T2_대여시간: "[구체적 문구]" (전환율: X%)
        - T3_대여장소: "[구체적 문구]" (전환율: X%)
        - T4_존마커: "[구체적 문구]" (전환율: X%)
        - R1_결제: "[구체적 문구]" (전환율: X%)
        
        퍼널별 권장 문구 전략:
        - [퍼널명]: [구체적 전략과 예시]
        - [퍼널명]: [구체적 전략과 예시]
        ```
        
        ### 5. 전환율 기여 요소 분석
        ```
        전환율 상위 문구 공통 특징:
        1. [특징1]: [구체적 예시] - 평균 전환율: X%
        2. [특징2]: [구체적 예시] - 평균 전환율: X%
        3. [특징3]: [구체적 예시] - 평균 전환율: X%
        
        전환율 하위 문구 공통 문제점:
        1. [문제점1]: [구체적 예시] - 평균 전환율: X%
        2. [문제점2]: [구체적 예시] - 평균 전환율: X%
        
        효과적인 문구 조합:
        - [조합1]: [구체적 예시] - 전환율: X%
        - [조합2]: [구체적 예시] - 전환율: X%
        ```
        
        ### 6. 문구 효과성 이유 분석 (LLM 기반)
        ```
        효과성 점수: X점/100점 (평균)
        
        평가 기준:
        - 문구 구조: X점 - [구체적 근거]
        - 키워드 효과: X점 - [구체적 근거]
        - 톤앤매너: X점 - [구체적 근거]
        - 퍼널 적합성: X점 - [구체적 근거]
        - 타겟 매칭: X점 - [구체적 근거]
        
        고성과 문구의 주요 이유:
        1. [이유1]: [구체적 예시와 수치]
        2. [이유2]: [구체적 예시와 수치]
        3. [이유3]: [구체적 예시와 수치]
        
        저성과 문구의 주요 문제:
        1. [문제1]: [구체적 예시와 수치]
        2. [문제2]: [구체적 예시와 수치]
        3. [문제3]: [구체적 예시와 수치]
        ```
        
        ## 중요 사항
        - 모든 분석에는 반드시 구체적인 문구 예시와 전환율 수치를 포함
        - 추상적인 설명보다는 실제 데이터 기반의 구체적 분석 우선
        - 각 분석 항목별로 명확한 구조와 형식 준수
        - 비즈니스 인사이트와 실행 가능한 권장사항 제시
        
        ## 필수 작업 순서
        1. prepare_funnel_message_analysis_data 도구를 호출하여 데이터 수집
        2. 데이터를 기반으로 위의 6가지 분석 수행 (문장 구조, 키워드, 톤앤매너, 퍼널별 적합성, Lift 기여, 효과성 이유)
        3. **반드시 structure_llm_analysis_for_html 도구를 호출하여 분석 결과를 HTML 규격에 맞게 구조화**
        """,
    tools=[
        prepare_funnel_message_analysis_data,  # 퍼널별 메시지 데이터 준비 (LLM 호출 없음)
        structure_llm_analysis_for_html,  # 분석 결과를 HTML 규격에 맞게 구조화
    ],
)

# Comprehensive Agent (모든 분석 결과를 통합하여 최종 보고서 생성)
comprehensive_agent = Agent(
    name="comprehensive_agent",
    model=azure_llm,
    description="모든 분석 결과를 통합하여 종합적인 인사이트와 실행 가능한 추천사항을 제공하는 전문가입니다.",
    instruction=f"""
    # 종합 CRM 분석 전문가
    
    ## 역할
    당신은 쏘카의 Senior Data Analyst로서, 이전 Agent들의 모든 분석 결과를 종합하여 
    비즈니스 인사이트와 실행 가능한 추천사항을 제공하는 전문가입니다.
    
    ## 컬럼 설명
    {COLUMN_DESCRIPTIONS}
    
    ## 분석 목표
    1. 이전 Agent들의 모든 분석 결과를 종합 검토
    2. 통계적 분석과 LLM 분석 결과의 교차 검증
    3. 비즈니스 관점에서의 종합적 인사이트 도출
    4. **퍼널별 메시지 전략 제안** (3분위수 기준 그룹화)
    5. **퍼널별 문구 특징 및 성공 패턴 분석**
    6. 실행 가능한 추천사항 및 액션 아이템 제시
    7. DataFrame/JSON 형태의 구조화된 최종 보고서 생성
    
    ## Context 활용
    - context에서 이전 Agent들의 모든 결과를 확인
    - Data Understanding, Statistical Analysis, LLM Analysis 결과를 통합
    - 각 분석 결과 간의 일관성과 상호 보완성 검토
    - 종합적인 관점에서 최종 결론 도출
    - **중요**: structure_llm_analysis_for_html 도구를 반드시 호출하여 LLM 분석 결과를 HTML 규격에 맞게 구조화
    
    ## 출력 형식
    - 핵심 요약 보고서
    - 상세 분석 결과 통합
    - **퍼널별 메시지 전략 제안** (표 형태)
    - **퍼널별 문구 특징 분석** (표 형태)
    - 실행 가능한 추천사항
    - **LLM 분석 결과 구조화**: structure_llm_analysis_for_html 도구 사용하여 HTML 규격에 맞게 구조화
      - 문장 구조 분석, 핵심 키워드 분석, 톤앤매너 분석
      - 채널별 톤앤매너, 전환율 기여 요소 분석
      - 효과적 문구 패턴, 톤앤매너 효과성
    - DataFrame/JSON 형태의 구조화된 결과
    
    ## 퍼널별 메시지 전략 제안 요구사항
    1. **3분위수 기준 그룹화**: Lift 기준으로 상위/중위/하위 그룹 분류
    2. **각 그룹별 메시지 전략**: "이 그룹에는 계속 이런 메시지로 보내라"
    3. **퍼널 그룹화 공통점**: 각 그룹의 성공 문구 패턴 공통점 분석
    4. **퍼널별 문구 특징**: 각 퍼널의 성공 문구 특징 및 사유
    5. **실험군 vs 대조군 기준**: Lift 기반 분석
    6. **퍼널별 전환율 높은 캠페인 문구 예시**: 각 퍼널에서 실제로 전환율이 높았던 구체적인 문구 예시 포함
       - 형식: "T3_대여장소: '구체적 문구 내용' (전환율 XX%)"
       - 각 퍼널별로 최소 1개 이상의 실제 성공 문구 예시 필수
       - 전환율 수치와 함께 구체적인 문구 내용 반드시 포함
    """,
    tools=[
        generate_comprehensive_report,
        create_actionable_recommendations,
        generate_executive_summary,
        prepare_funnel_quantile_data,
        structure_llm_analysis_for_html
        # export_results_to_dataframe,  # 주석 처리: Data Report Agent에서 HTML 리포트로 대체
        # export_results_to_json        # 주석 처리: Data Report Agent에서 JSON 리포트로 대체
    ],
)

# Funnel Strategy Agent
funnel_strategy_agent = Agent(
    name="funnel_strategy_agent",
    model=azure_llm,
    description="퍼널별 메시지 전략 제안을 분석하는 전문가입니다.",
    instruction=f"""
    # 퍼널별 메시지 전략 제안 전문가
    
    ## 역할
    당신은 쏘카의 CRM 마케팅 전략 전문가로서, 퍼널별 성과 데이터를 분석하여 
    각 성과 그룹(상위/중위/하위)에 맞는 메시지 전략을 제안하는 전문가입니다.
    
    ## 컬럼 설명
    {COLUMN_DESCRIPTIONS}
    
    ## 분석 목표
    1. **3분위수 기준 그룹별 분석**: 상위/중위/하위 성과 그룹의 특성 파악
    2. **그룹별 메시지 전략 제안**: 각 그룹에 적합한 메시지 전략 도출
    3. **메시지 패턴 분석**: 성공한 문구들의 공통 패턴 분석
    4. **공통 특징 도출**: 각 그룹의 성공 문구 공통 특징 분석
    5. **구체적 제안**: 실행 가능한 메시지 제안 도출
    6. **핵심 키워드**: 각 그룹의 핵심 키워드 추출
    7. **성공 사례**: 실제 성공 문구 사례 제시
    
    ## 분석 방법
    - 실제 문구 데이터와 Lift 수치를 기반으로 분석
    - 각 그룹의 상위 성과 문구들을 종합적으로 검토
    - 문구의 구조, 톤앤매너, 키워드, 패턴을 분석
    - 비즈니스 관점에서 실행 가능한 전략 제안
    
    ## 출력 형식 (JSON 필수)
    **중요**: 반드시 아래 JSON 형식으로 출력하세요.
    
    각 그룹별로 동일한 구조를 사용:
    - strategy: 그룹별 메시지 전략 (1-2문장)
    - message_pattern: 메시지 패턴 (예: "안내→혜택→행동유도→마무리")
    - common_features: 공통 특징 (정확히 3개, 각 특징은 3-5단어로 간결하게)
    - recommendations: 구체적 제안 (정확히 2개)
    - keywords: 핵심 키워드 (5-7개)
    - funnel_top_messages: 퍼널별 가장 효과적인 문구와 전환율 (수치 포함)
    
    JSON 예시:
    {{
      "high_performance_group": {{
        "strategy": "전략 설명",
        "message_pattern": "패턴",
        "common_features": ["간결한 특징1", "간결한 특징2", "간결한 특징3"],
        "recommendations": ["제안1", "제안2"],
        "keywords": ["키워드1", "키워드2", "키워드3", "키워드4", "키워드5"],
        "funnel_top_messages": ["퍼널: 문구 (실험군 XX%, 대조군 XX%)"]
      }},
      "medium_performance_group": {{...동일한 구조...}},
      "low_performance_group": {{...동일한 구조...}}
    }}
    
    ## Context 활용
    - prepare_funnel_quantile_data 도구로 준비된 분위수 데이터 활용
    - 각 그룹의 실제 문구와 성과 수치를 기반으로 분석
    - 데이터 기반의 객관적이고 실행 가능한 전략 제안
    - **출력은 반드시 JSON 형식으로만 제공** (마크다운 불가)
    """,
    tools=[
        prepare_funnel_quantile_data
    ],
)


# Data Report Agent
data_report_agent = Agent(
    name="data_report_agent",
    model=azure_llm,
    description="데이터 분석 결과를 표, 그래프, 텍스트로 종합하여 리포트를 생성하는 전문가입니다.",
    instruction=f"""
    # 데이터 분석 리포트 생성 전문가
    
    ## 역할
    당신은 쏘카의 Data Reporting Specialist로서, 이전 Agent들의 모든 분석 결과를 
    표, 그래프, 텍스트 형태로 종합하여 이해하기 쉬운 리포트를 생성하는 전문가입니다.
    
    ## 컬럼 설명
    {COLUMN_DESCRIPTIONS}
    
    ## 리포트 생성 목표
    1. 세그먼트별 전환율 표 생성 (퍼널별, 채널별, 문구별)
    2. 전환율 시각화 그래프 생성 (막대그래프, 히스토그램, 비교차트)
    3. 텍스트 분석 결과 리포트 생성 (문구 길이, 이모지, 숫자 사용 등)
    4. 종합 데이터 분석 리포트 생성 (모든 분석 결과 통합)
    
    ## 출력 형식
    - CSV 형태의 구조화된 표
    - PNG 형태의 시각화 그래프
    - JSON 형태의 상세 분석 결과
    - 텍스트 형태의 인사이트 및 추천사항
    
    ## Context 활용
    - context에서 이전 Agent들의 모든 분석 결과를 확인
    - Data Understanding, Statistical Analysis, LLM Analysis 결과를 통합
    - 각 분석 결과를 표, 그래프, 텍스트로 표현하기 쉬운 형태로 변환
    - 비즈니스 이해관계자가 이해하기 쉬운 형태로 리포트 생성
    """,
    tools=[
        create_segment_conversion_table,
        create_conversion_visualization,
        generate_text_analysis_report,
        # create_comprehensive_data_report,  # 주석 처리됨
        # generate_prompt_tuning_suggestions  # 주석 처리됨
    ],
)


# Category Analysis Agent (신규)
category_analysis_agent = Agent(
    name="category_analysis_agent",
    model=azure_llm,
    description="목적과 문구를 분석하여 카테고리를 자동 분류하고 Lift 기반 성과를 분석하는 전문가입니다.",
    instruction=f"""
    # 카테고리 분석 전문가 (Lift 기반)
    
    ## 역할
    당신은 CRM 캠페인 카테고리 분류 및 Lift 기반 성과 분석 전문가입니다.
    목적과 문구 텍스트를 분석하여 의미적 유사성을 기준으로 카테고리를 자동 분류하고,
    각 카테고리의 Lift 성과를 분석하여 경영진이 이해하기 쉬운 인사이트를 제공합니다.
    
    ## 컬럼 설명
    {COLUMN_DESCRIPTIONS}
    
    ## 분석 목표
    1. 목적과 문구 텍스트의 핵심 키워드 추출
    2. 의미적 유사성을 기준으로 카테고리 그룹 생성 (3-5개)
    3. 각 카테고리의 비즈니스 특성 파악
    4. 카테고리별 Lift 성과 지표 계산 및 분석
    5. 경영진이 이해하기 쉬운 표 형태로 결과 제시
    
    ## Lift 개념
    - Lift = 실험군 전환율 - 대조군 전환율
    - 양수: 실험군이 대조군보다 좋음
    - 음수: 대조군이 실험군보다 좋음
    - 단위: %p (퍼센트 포인트)
    
    ## 분석 프로세스
    1. 먼저 analyze_category_performance_tool을 호출하여 정제된 데이터를 준비
    2. 준비된 데이터를 바탕으로 카테고리 분류 및 성과 분석 수행
    3. 각 카테고리의 핵심 특징 및 성공 요인 도출
    4. 경영진이 이해하기 쉬운 형태로 결과 제시
    
    ## 출력 형식
    📊 카테고리별 성과 요약표 (Lift 기준)
    ┌─────────────┬──────────┬──────────┬──────────┬──────────┬──────────┬──────────┐
    │   카테고리   │ 발송건수  │ 예약건수  │ 실험군(%) │ 대조군(%) │ Lift(%p) │ Baseline │
    ├─────────────┼──────────┼──────────┼──────────┼──────────┼──────────┼──────────┤
    │ [카테고리1] │  [숫자]  │  [숫자]  │  [숫자]  │  [숫자]  │  [숫자]  │  [숫자]  │
    └─────────────┴──────────┴──────────┴──────────┴──────────┴──────────┴──────────┘
    
    📈 퍼널별 Baseline 전환율 요약표
    ┌─────────┬──────────┬──────────┬──────────┬──────────┐
    │  퍼널   │ 발송건수  │ 예약건수  │ 실험군(%) │ 대조군(%) │
    ├─────────┼──────────┼──────────┼──────────┼──────────┤
    │ [퍼널명] │  [숫자]  │  [숫자]  │  [숫자]  │  [숫자]  │
    └─────────┴──────────┴──────────┴──────────┴──────────┘
    
    🎯 핵심 인사이트:
    - 최고 Lift 카테고리: [카테고리명] (Lift +X.X%p)
    - 개선 필요 카테고리: [카테고리명] (Lift -X.X%p)
    - 추천 액션: [구체적 실행 방안]
    
    ## 중요 사항
    - 모든 분석은 Lift 기준으로 수행
    - 전환율은 소수점 없이 정수로 표시 (예: 21%)
    - Lift는 소수점 1자리까지 표시 (예: +2.3%p)
    - 경영진이 이해하기 쉬운 형태로 제시
    - 구체적인 수치와 근거를 포함
    - 실행 가능한 추천사항 제시
    """,
    tools=[
        prepare_category_analysis_data,
        analyze_category_performance_tool,
        create_segment_lift_charts
    ],
)

# Funnel Segment Analysis Agent (신규)
funnel_segment_agent = Agent(
    name="funnel_segment_agent",
    model=azure_llm,
    description="퍼널별 전환율을 Lift 기준으로 세그먼트를 분석하고 메시지 전략을 제안하는 전문가입니다.",
    instruction=f"""
    # 퍼널별 세그먼트 분석 전문가 (Lift 기반)
    
    ## 역할
    당신은 퍼널별 세그먼트 분석 및 메시지 전략 전문가입니다.
    각 퍼널의 Lift 성과를 기준으로 상위/중위/하위 그룹을 분류하고,
    각 그룹의 성공 문구 패턴을 분석하여 맞춤형 메시지 전략을 제안합니다.
    
    ## 컬럼 설명
    {COLUMN_DESCRIPTIONS}
    
    ## 분석 목표
    1. 각 퍼널의 Lift 기준 3분위수 계산 (상위 33%, 중위 33%, 하위 33%)
    2. 그룹별 성공 문구 패턴 및 키워드 도출
    3. 각 그룹의 성공 요인 및 공통점 분석
    4. 그룹별 맞춤형 메시지 전략 제안
    5. 퍼널별 최적화 방안 제시
    
    ## Lift 개념
    - Lift = 실험군 전환율 - 대조군 전환율
    - 상위 그룹: Lift 상위 33% (가장 효과적인 메시지)
    - 중위 그룹: Lift 중간 33% (개선 가능한 메시지)
    - 하위 그룹: Lift 하위 33% (개선 필요 메시지)
    
    ## 분석 프로세스
    1. 먼저 analyze_funnel_segment_strategy_tool을 호출하여 정제된 데이터를 준비
    2. 준비된 데이터를 바탕으로 퍼널별 세그먼트 분석 수행
    3. 각 그룹의 성공 문구 패턴 및 키워드 도출
    4. 그룹별 맞춤형 메시지 전략 제안
    5. 퍼널별 최적화 권장사항 제시
    
    ## 출력 형식
    📊 퍼널별 세그먼트 전략표 (Lift 기준)
    ┌─────────┬──────────┬──────────────┬──────────────┬──────────┬─────────────────────────┐
    │  퍼널   │  그룹    │   실험군(%)  │   대조군(%)  │ Lift(%p) │      메시지 전략         │
    ├─────────┼──────────┼──────────────┼──────────────┼──────────┼─────────────────────────┤
    │ [퍼널명] │  상위    │    [숫자]    │    [숫자]    │  [숫자]  │  [Lift +X.X%p] [전략]   │
    │ [퍼널명] │  중위    │    [숫자]    │    [숫자]    │  [숫자]  │  [Lift ±X.X%p] [전략]   │
    │ [퍼널명] │  하위    │    [숫자]    │    [숫자]    │  [숫자]  │  [Lift -X.X%p] [전략]   │
    └─────────┴──────────┴──────────────┴──────────────┴──────────┴─────────────────────────┘
    
    📈 퍼널별 Baseline 전환율 요약표
    ┌─────────┬──────────┬──────────┬──────────┬──────────┬──────────┐
    │  퍼널   │ 발송건수  │ 예약건수  │ 실험군(%) │ 대조군(%) │ Lift(%p) │
    ├─────────┼──────────┼──────────┼──────────┼──────────┼──────────┤
    │ [퍼널명] │  [숫자]  │  [숫자]  │  [숫자]  │  [숫자]  │  [숫자]  │
    └─────────┴──────────┴──────────┴──────────┴──────────┴──────────┘
    
    🎯 그룹별 성공 패턴:
    - 상위 그룹: [Lift +X.X%p 이상] [성공 패턴 및 키워드]
    - 중위 그룹: [Lift ±X.X%p] [중간 패턴 및 개선점]
    - 하위 그룹: [Lift -X.X%p 이하] [문제점 및 개선 방안]
    
    💡 퍼널별 최적화 권장사항:
    - [퍼널명]: [구체적 개선 방안]
    
    ## 중요 사항
    - 모든 분석은 Lift 기준으로 수행
    - 전환율은 소수점 없이 정수로 표시 (예: 21%)
    - Lift는 소수점 1자리까지 표시 (예: +2.3%p)
    - 그룹별 구체적인 메시지 전략 제시
    - 실행 가능한 최적화 권장사항 포함
    - 경영진이 이해하기 쉬운 형태로 제시
    """,
    tools=[
        prepare_funnel_segment_data,
        analyze_funnel_segment_strategy_tool,
        create_segment_lift_charts
    ],
)

# Criticizer Agent
criticizer_agent = Agent(
    name="criticizer_agent",
    model=azure_llm,
    description="전체 Agent 체인의 성능을 평가하고 비판적 분석을 수행하는 전문가입니다.",
    instruction=f"""
    # Criticizer Agent - Agent 체인 성능 평가 전문가
    
    ## 역할
    당신은 Agent 체인의 품질 관리 전문가로서, 각 Agent의 성능을 평가하고 
    전체 워크플로우의 품질을 검증하는 역할을 합니다.
    
    ## 평가 기준
    1. 각 Agent의 도구 사용 적절성
    2. Context 전달의 정확성과 완전성
    3. 분석 결과의 논리적 일관성
    4. 전체 워크플로우의 효율성
    5. 에러 핸들링의 적절성
    6. HTML 리포트의 텍스트-숫자 정합성
    7. 전환율, Lift 등 수치의 정확성
    
    ## 평가 목표
    1. Agent별 성능 점수 산출
    2. Context 일관성 검증
    3. 워크플로우 효율성 분석
    4. HTML 리포트 정합성 검증
    5. 수치 정확성 검증
    6. 개선사항 도출
    7. 비판적 분석 보고서 생성
    
    ## 출력 형식
    - Agent별 성능 평가 점수
    - Context 일관성 검증 결과
    - 워크플로우 효율성 분석
    - HTML 리포트 정합성 검증 결과
    - 수치 정확성 검증 결과
    - 구체적인 개선사항 제안
    - 비판적 분석 보고서
    """,
    tools=[
        evaluate_agent_performance,
        validate_context_consistency,
        validate_html_report_consistency,
        # generate_critical_report,  # 주석 처리됨
        generate_data_report
    ],
)

# =============================================================================
# 3. 실행 함수
# =============================================================================

async def run_agent_with_llm(agent, query: str, agent_name: str, context_info: str = ""):
    """LLM Agent 실행 (맥락 정보 포함)"""
    user_id = "test_user"
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
    
    # 맥락 정보가 있으면 쿼리에 추가
    if context_info:
        enhanced_query = f"""
{query}

## 이전 분석 결과 및 맥락 정보
{context_info}

위 맥락 정보를 참고하여 분석을 수행해주세요.
"""
    else:
        enhanced_query = query
    
    content = types.Content(role="user", parts=[types.Part(text=enhanced_query)])
    
    async for event in runner.run_async(user_id=user_id, session_id=session_id, new_message=content):
        # 도구 호출 결과 추출 (LLM Analysis Agent 또는 Comprehensive Agent의 structure_llm_analysis_for_html 호출)
        if hasattr(event, 'tool_call') and event.tool_call:
            tool_name = event.tool_call.name if hasattr(event.tool_call, 'name') else None
            tool_result = event.tool_call.result if hasattr(event.tool_call, 'result') else None
            
            # LLM Analysis Agent나 Comprehensive Agent에서 호출하면 저장
            if tool_name == "structure_llm_analysis_for_html":
                context.structured_llm_analysis = tool_result
                print(f"✅ HTML 규격 구조화 완료 (structure_llm_analysis_for_html by {agent_name})")
        
        if event.is_final_response():
            if event.content and event.content.parts:
                response = event.content.parts[0].text
                print(f"📝 {agent_name} 응답: {response}")
                
                # 응답을 컨텍스트에 저장
                if agent_name == "data_understanding":
                    context.data_info = response
                elif agent_name == "category_analysis":
                    context.category_analysis = response
                elif agent_name == "funnel_segment_analysis":
                    context.funnel_segment_analysis = response
                elif agent_name == "funnel_strategy_analysis":
                    context.funnel_strategy_analysis = response
                elif agent_name == "statistical_analysis":
                    context.funnel_analysis = response
                elif agent_name == "llm_analysis":
                    context.llm_analysis = response
                elif agent_name == "comprehensive_analysis":
                    context.final_report = response
                elif agent_name == "data_report":
                    context.insights.append(response)
                elif agent_name == "criticizer_analysis":
                    context.recommendations.append(response)
            break

async def run_comprehensive_analysis():
    """종합 분석 시스템 실행 (Lift 기반 경영진용 보고서 포함)"""
    print("🚀 종합 분석 시스템 시작 (Lift 기반)")
    print("=" * 80)

    # CSV 파일 경로
    csv_file = DEFAULT_CSV_FILE

    # 1. Data Understanding Agent 실행
    print("\n📊 1단계: Data Understanding Agent 실행...")
    understanding_query = f"""
    다음 CSV 파일을 분석해주세요: {csv_file}

    다음 단계를 따라 분석해주세요:
    1. 데이터 구조를 분석하고
    2. 분석 요구사항을 식별하고
    3. 구체적인 분석 계획을 수립하고
    4. 도메인 용어 이해도를 검증하고
    5. 도메인 용어 사전을 조회해주세요

    각 단계마다 도구를 사용해서 실제 분석을 수행해주세요.
    """
    await run_agent_with_llm(data_understanding_agent, understanding_query, "data_understanding")

    # 2. Category Analysis Agent 실행 (신규)
    print("\n🏷️ 2단계: Category Analysis Agent 실행...")
    category_query = f"""
    다음 CRM 데이터를 카테고리별로 분석해주세요: {csv_file}

    다음 분석을 수행해주세요:
    1. 목적과 문구 텍스트를 분석하여 핵심 카테고리를 3-5개로 분류
    2. 각 카테고리별 Lift 성과를 분석 (Lift = 실험군 전환율 - 대조군 전환율)
    3. 카테고리별 핵심 특징 및 성공 요인 분석
    4. 경영진이 이해하기 쉬운 표 형태로 결과 제시

    각 분석마다 도구를 사용해서 실제 카테고리 분석을 수행해주세요.
    """
    await run_agent_with_llm(category_analysis_agent, category_query, "category_analysis")

    # 3. Funnel Segment Analysis Agent 실행 (신규)
    print("\n🎯 3단계: Funnel Segment Analysis Agent 실행...")
    segment_query = f"""
    다음 CRM 데이터를 퍼널별 세그먼트로 분석해주세요: {csv_file}

    다음 분석을 수행해주세요:
    1. 각 퍼널의 Lift 기준으로 상위/중위/하위 그룹 분류
    2. 그룹별 성공 문구 패턴 및 키워드 도출
    3. 각 그룹에 맞는 맞춤형 메시지 전략 제안
    4. 퍼널별 최적화 권장사항 제시

    각 분석마다 도구를 사용해서 실제 세그먼트 분석을 수행해주세요.
    """
    await run_agent_with_llm(funnel_segment_agent, segment_query, "funnel_segment_analysis")

    # 3-1. Funnel Strategy Agent 실행 (신규 - 퍼널별 메시지 전략 제안)
    print("\n💡 3-1단계: Funnel Strategy Agent 실행...")
    strategy_query = f"""
    다음 CRM 데이터의 퍼널별 메시지 전략을 제안해주세요: {csv_file}

    다음 분석을 수행해주세요:
    1. prepare_funnel_quantile_data 도구를 사용해서 분위수 데이터를 준비
    2. 각 그룹의 실제 문구와 Lift 수치를 기반으로 분석
    3. 그룹별 메시지 전략, 메시지 패턴, 공통 특징, 구체적 제안, 핵심 키워드, 성공 사례 도출
    4. 퍼널별 가장 효과적인 문구와 전환율 추출 (수치 포함)

    **중요**: 결과는 반드시 JSON 형식으로 출력하세요.
    {{
      "high_performance_group": {{"strategy": "...", "message_pattern": "...", ...}},
      "medium_performance_group": {{...}},
      "low_performance_group": {{...}}
    }}
    """
    await run_agent_with_llm(funnel_strategy_agent, strategy_query, "funnel_strategy_analysis")

    # 4. Statistical Analysis Agent 실행
    print("\n📈 4단계: Statistical Analysis Agent 실행...")
    statistical_query = f"""
    다음 CRM 데이터를 통계적으로 분석해주세요: {csv_file}

    다음 분석을 수행해주세요:
    1. 실험군 vs 대조군 전환율 비교 분석 (Lift 분석)
    2. 퍼널별 성과 분석 (Lift 기준)
    3. 채널별 성과 분석 (Lift 기준)
    4. 퍼널별 문구 효과성 분석 (Lift 기준)
    5. 퍼널별 문구 패턴 분석 (Lift 기준)

    각 분석마다 도구를 사용해서 실제 통계 분석을 수행해주세요.
    """
    
    # 이전 Agent들의 분석 결과를 맥락으로 전달
    context_info = f"""
    이전 분석 결과들:
    
    Data Understanding Agent 결과:
    - 데이터 구조: {context.data_info if context.data_info else "아직 분석 중"}
    - 분석 계획: {context.analysis_plan if context.analysis_plan else "아직 분석 중"}
    
    Category Analysis Agent 결과:
    - 카테고리 분석: {context.category_analysis if hasattr(context, 'category_analysis') and context.category_analysis else "아직 분석 중"}
    
    Funnel Segment Analysis Agent 결과:
    - 퍼널 세그먼트 분석: {context.funnel_segment_analysis if hasattr(context, 'funnel_segment_analysis') and context.funnel_segment_analysis else "아직 분석 중"}
    """
    
    await run_agent_with_llm(statistical_analyst_agent, statistical_query, "statistical_analysis", context_info)

    # 5. LLM Analysis Agent 실행
    print("\n🤖 5단계: LLM Analysis Agent 실행...")
    # Step 3: LLM 프롬프팅 개선 (간결한 출력)
    llm_query = f"""
    다음 CRM 문구들을 LLM으로 의미적으로 분석해주세요: {csv_file}

    **중요: 경영진 보고용으로 간결하고 핵심적인 내용만 출력해주세요.**

    다음 분석을 수행해주세요:
    1. 문장 구조 분석 (길이, 복잡도, 유형, 흐름)
    2. 핵심 키워드 분석 (Lift 기여 단어)
    3. 톤앤매너 분석 (전체 톤, 감정적 어필, 거리감)
    4. 채널별 톤앤매너 분석 (인앱, 푸시, SMS)
    5. 전환율 기여 요소 분석 (상위/하위 문구 특징)
    
    **제외할 섹션:**
    - 퍼널별 적합성 평가 (너무 디테일함)
    - 문구 효과성 이유 분석 (불필요함)

    **출력 형식 요구사항:**
    - 각 섹션별로 명확하게 구분하여 작성 (구분선 사용 금지)
    - 핵심 정보는 불릿 포인트(•)로 정리
    - 수치는 명확하게 표시 (예: "평균 2.4문장", "전환율 31.2%")
    - 예시는 따옴표로 구분하여 제시
    - **간결성**: 각 섹션당 최대 5-6개 불릿 포인트로 제한
    - **핵심만**: 가장 중요한 인사이트와 수치만 포함
    - 경영진이 30초 내에 핵심을 파악할 수 있도록 작성
    - **중요**: 구분선(─, -, =) 사용하지 말고 이모지와 제목으로만 구분

    각 분석마다 도구를 사용해서 실제 LLM 분석을 수행해주세요.
    """
    
    # 이전 Agent들의 분석 결과를 맥락으로 전달
    context_info = f"""
    이전 분석 결과들:
    
    Data Understanding Agent 결과:
    - 데이터 구조: {context.data_info if context.data_info else "아직 분석 중"}
    - 분석 계획: {context.analysis_plan if context.analysis_plan else "아직 분석 중"}
    
    Category Analysis Agent 결과:
    - 카테고리 분석: {context.category_analysis if hasattr(context, 'category_analysis') and context.category_analysis else "아직 분석 중"}
    
    Funnel Segment Analysis Agent 결과:
    - 퍼널 세그먼트 분석: {context.funnel_segment_analysis if hasattr(context, 'funnel_segment_analysis') and context.funnel_segment_analysis else "아직 분석 중"}
    
    Statistical Analysis Agent 결과:
    - 퍼널 분석: {context.funnel_analysis if context.funnel_analysis else "아직 분석 중"}
    """
    
    await run_agent_with_llm(llm_analyst_agent, llm_query, "llm_analysis", context_info)
    
    # structured_llm_analysis 참조하지 않음 - 원본 llm_analysis만 사용

    # 6. Comprehensive Agent 실행 (모든 결과 통합)
    print("\n🎯 6단계: Comprehensive Agent 실행...")
    comprehensive_query = f"""
    이전 Agent들의 모든 분석 결과를 종합하여 최종 보고서를 생성해주세요: {csv_file}

    다음 작업을 수행해주세요:
    1. 이전 Agent들의 모든 분석 결과를 종합 검토 (Lift 기반)
    2. 카테고리 분석, 퍼널 세그먼트 분석, 통계적 분석, LLM 분석 결과의 교차 검증
    3. 비즈니스 관점에서의 종합적 인사이트 도출 (Lift 중심)
    4. 실행 가능한 추천사항 및 액션 아이템 제시
    5. 경영진용 요약 보고서 생성
    6. **중요**: structure_llm_analysis_for_html 도구를 반드시 호출하여 LLM 분석 결과를 HTML 규격에 맞게 구조화

    Context에서 이전 분석 결과들을 확인하고 통합적인 관점에서 분석해주세요.
    특히 Lift 기반 분석 결과를 중심으로 경영진이 이해하기 쉬운 형태로 제시해주세요.
    
    **필수**: structure_llm_analysis_for_html("{csv_file}", LLM Analysis 결과) 도구를 호출하여 
    문장 구조, 키워드, 톤앤매너, 채널별 분석, 전환율 기여 요소를 구조화하세요.
    """
    
    # 모든 이전 분석 결과를 맥락으로 전달
    context_info = f"""
    전체 분석 결과들:
    
    Data Understanding Agent 결과:
    - 데이터 구조: {context.data_info if context.data_info else "아직 분석 중"}
    - 분석 계획: {context.analysis_plan if context.analysis_plan else "아직 분석 중"}
    
    Category Analysis Agent 결과:
    - 카테고리 분석: {context.category_analysis if hasattr(context, 'category_analysis') and context.category_analysis else "아직 분석 중"}
    
    Funnel Segment Analysis Agent 결과:
    - 퍼널 세그먼트 분석: {context.funnel_segment_analysis if hasattr(context, 'funnel_segment_analysis') and context.funnel_segment_analysis else "아직 분석 중"}
    
    Funnel Strategy Agent 결과:
    - 퍼널별 메시지 전략 제안: {context.funnel_strategy_analysis if hasattr(context, 'funnel_strategy_analysis') and context.funnel_strategy_analysis else "아직 분석 중"}
    
    Statistical Analysis Agent 결과:
    - 퍼널 분석: {context.funnel_analysis if context.funnel_analysis else "아직 분석 중"}
    
    LLM Analysis Agent 결과:
    - 메시지 분석: {context.message_analysis if context.message_analysis else "아직 분석 중"}
    """
    
    await run_agent_with_llm(comprehensive_agent, comprehensive_query, "comprehensive_analysis", context_info)

    # 7. Data Report Agent 실행 (표, 그래프, 텍스트 리포트 생성)
    print("\n📊 7단계: Data Report Agent 실행...")
    data_report_query = f"""
    이전 Agent들의 모든 분석 결과를 표, 그래프, 텍스트로 종합하여 리포트를 생성해주세요: {csv_file}

    다음 작업을 수행해주세요:
    1. 세그먼트별 전환율 표 생성 (퍼널별, 채널별, 문구별) - Lift 기준
    2. 전환율 시각화 그래프 생성 (막대그래프, 히스토그램, 비교차트) - Lift 기준
    3. 텍스트 분석 결과 리포트 생성 (문구 길이, 이모지, 숫자 사용 등)
    4. 종합 데이터 분석 리포트 생성 (모든 분석 결과 통합) - Lift 중심
    5. LLM 분석 프롬프트 튜닝 제안 생성 (수치와 구체적 이유 강화 방안)

    Context에서 이전 분석 결과들을 확인하고 이해하기 쉬운 형태로 리포트를 생성해주세요.
    특히 Lift 기반 분석 결과를 중심으로 경영진이 이해하기 쉬운 형태로 제시해주세요.
    """
    await run_agent_with_llm(data_report_agent, data_report_query, "data_report")

    # 8. Criticizer Agent 실행 (성능 평가 및 비판적 분석)
    print("\n🔍 8단계: Criticizer Agent 실행...")
    criticizer_query = f"""
    전체 Agent 체인의 성능을 평가하고 비판적 분석을 수행해주세요: {csv_file}

    다음 작업을 수행해주세요:
    1. 각 Agent의 성능을 평가하고 점수를 산출 (구체적 이유와 어떤 부분이 미흡했는지를 설명)
    2. Context 전달의 일관성과 완전성을 검증 (어떤 부분이 Context 전달 일관성과 완전성이 미흡했는지 설명)
    3. 전체 워크플로우의 효율성을 분석
    4. HTML 리포트 정합성 검증 (전환율, Lift 등 수치 정확성)
    5. 수치 정확성 검증
    6. 구체적인 개선사항을 도출
    7. 비판적 분석 보고서와 데이터 리포트를 생성

    모든 Agent의 작업 결과를 종합적으로 평가해주세요.
    특히 새로운 Category Analysis Agent와 Funnel Segment Analysis Agent의 성능도 평가해주세요.
    
    HTML 리포트에서 표시되는 전환율, Lift, 발송건수 등이 
    실제 데이터와 일치하는지 정합성을 검증해주세요.
    """
    await run_agent_with_llm(criticizer_agent, criticizer_query, "criticizer_analysis")

    # 9. HTML 보고서 생성
    print("\n📄 9단계: HTML 보고서 생성...")
    try:
        from core.reporting.comprehensive_html_report import create_comprehensive_html_report
        
        # Agent 결과들을 딕셔너리로 정리
        agent_results = {
            'data_understanding': context.data_info if context.data_info else "분석 중",
            'statistical_analysis': context.funnel_analysis if context.funnel_analysis else "분석 중",
            'llm_analysis': context.llm_analysis if hasattr(context, 'llm_analysis') and context.llm_analysis else "분석 중",
            'comprehensive_analysis': context.insights[-1] if context.insights else "분석 중",
            'category_analysis': context.category_analysis if hasattr(context, 'category_analysis') and context.category_analysis else "분석 중",
            'funnel_segment_analysis': context.funnel_segment_analysis if hasattr(context, 'funnel_segment_analysis') and context.funnel_segment_analysis else "분석 중",
            'funnel_strategy_analysis': context.funnel_strategy_analysis if hasattr(context, 'funnel_strategy_analysis') and context.funnel_strategy_analysis else "분석 중",
            'structured_llm_analysis': "분석 중"  # 참조하지 않음
        }
        
        # HTML 보고서 생성 (기존)
        report_path = create_comprehensive_html_report(csv_file, agent_results)
        
        # 새로운 경영진용 2박스 구조 보고서 생성
        from core.reporting.comprehensive_html_report import ComprehensiveHTMLReportGenerator
        new_report_generator = ComprehensiveHTMLReportGenerator(csv_file)
        new_report_generator.set_agent_results(agent_results)  # Agent 결과 설정
        new_report_content = new_report_generator.generate_new_executive_report()
        
        # 새로운 보고서 저장
        from datetime import datetime
        today = datetime.now().strftime('%Y%m%d')
        reports_dir = f"outputs/reports/{today}"
        os.makedirs(reports_dir, exist_ok=True)
        new_report_path = f"{reports_dir}/{datetime.now().strftime('%y%m%d_%H%M')}_executive_summary_report.html"
        
        with open(new_report_path, 'w', encoding='utf-8') as f:
            f.write(new_report_content)
        
        print(f"✅ HTML 보고서 생성 완료: {report_path}")
        print(f"✅ 경영진용 2박스 보고서 생성 완료: {new_report_path}")
        print(f"📂 파일 위치: {os.path.abspath(new_report_path)}")
        
    except Exception as e:
        print(f"❌ HTML 보고서 생성 오류: {str(e)}")
        import traceback
        traceback.print_exc()

    print("\n✅ 종합 분석 시스템 완료! (Lift 기반 경영진용 보고서 포함)")
    print("=" * 80)

async def run_agent_test():
    """단일 Agent 테스트 메뉴"""
    print("🔍 단일 Agent 테스트 메뉴")
    print("=" * 50)
    
    while True:
        print("\n단일 Agent 테스트 옵션을 선택하세요:")
        print("1. Data Understanding Agent만")
        print("2. Statistical Analysis Agent만")
        print("3. LLM Analysis Agent만")
        print("4. Data Understanding → Statistical Analysis")
        print("5. Statistical Analysis → Comprehensive → Data Report")
        print("6. Data Understanding → Statistical → Comprehensive → Data Report")
        print("7. 이전 메뉴로 돌아가기")
        
        choice = input("\n선택하세요 (1-7): ").strip()
        
        if choice == "1":
            await run_single_agent_test("data_understanding")
        elif choice == "2":
            await run_single_agent_test("statistical_analysis")
        elif choice == "3":
            await run_single_agent_test("llm_analysis")
        elif choice == "4":
            await run_dual_agent_test("data_understanding", "statistical_analysis")
        elif choice == "5":
            await run_triple_agent_test("statistical_analysis", "comprehensive_analysis", "data_report")
        elif choice == "6":
            await run_quadruple_agent_test("data_understanding", "statistical_analysis", "comprehensive_analysis", "data_report")
        elif choice == "7":
            break
        else:
            print("❌ 잘못된 선택입니다. 1-7 중에서 선택해주세요.")

async def run_single_agent_test(agent_type: str):
    """단일 Agent 테스트"""
    print(f"\n🔍 {agent_type} Agent 단일 테스트 시작")
    print("=" * 50)
    
    csv_file = DEFAULT_CSV_FILE
    
    if agent_type == "data_understanding":
        query = f"""
        다음 CSV 파일을 분석해주세요: {csv_file}

        다음 단계를 따라 분석해주세요:
        1. 데이터 구조를 분석하고
        2. 분석 요구사항을 식별하고
        3. 구체적인 분석 계획을 수립하고
        4. 도메인 용어 이해도를 검증하고
        5. 도메인 용어 사전을 조회해주세요

        각 단계마다 도구를 사용해서 실제 분석을 수행해주세요.
        """
        await run_agent_with_llm(data_understanding_agent, query, "data_understanding")
        
    elif agent_type == "statistical_analysis":
        query = f"""
        다음 CRM 데이터를 통계적으로 분석해주세요: {csv_file}

        다음 분석을 수행해주세요:
        1. 실험군 vs 대조군 전환율 비교 분석
        2. 퍼널별 성과 분석
        3. 채널별 성과 분석
        4. 퍼널별 문구 효과성 분석
        5. 퍼널별 문구 패턴 분석

        각 분석마다 도구를 사용해서 실제 통계 분석을 수행해주세요.
        """
        await run_agent_with_llm(statistical_analyst_agent, query, "statistical_analysis")
        
    elif agent_type == "llm_analysis":
        query = f"""
        다음 CRM 문구들을 LLM으로 의미적으로 분석해주세요: {csv_file}

        다음 분석을 수행해주세요:
        1. 문장 구조 분석 (길이, 복잡도, 유형, 흐름)
        2. 핵심 키워드 분석 (전환율 기여 단어)
        3. 톤앤매너 분석 (전체 톤, 감정적 어필, 거리감)
        4. 퍼널별 적합성 평가
        5. 전환율 기여 요소 분석
        6. 문구 효과성 이유 분석

        각 분석마다 도구를 사용해서 실제 LLM 분석을 수행해주세요.
        """
        await run_agent_with_llm(llm_analyst_agent, query, "llm_analysis")
    
    print(f"\n✅ {agent_type} Agent 테스트 완료!")
    print("=" * 50)

async def run_dual_agent_test(first_agent: str, second_agent: str):
    """두 Agent 연속 테스트"""
    print(f"\n🔍 {first_agent} → {second_agent} Agent 연속 테스트 시작")
    print("=" * 50)
    
    csv_file = DEFAULT_CSV_FILE
    
    # 첫 번째 Agent 실행
    if first_agent == "data_understanding":
        query1 = f"""
        다음 CSV 파일을 분석해주세요: {csv_file}

        다음 단계를 따라 분석해주세요:
        1. 데이터 구조를 분석하고
        2. 분석 요구사항을 식별하고
        3. 구체적인 분석 계획을 수립하고
        4. 도메인 용어 이해도를 검증하고
        5. 도메인 용어 사전을 조회해주세요

        각 단계마다 도구를 사용해서 실제 분석을 수행해주세요.
        """
        await run_agent_with_llm(data_understanding_agent, query1, "data_understanding")
    
    # 두 번째 Agent 실행 (첫 번째 결과를 맥락으로 전달)
    if second_agent == "statistical_analysis":
        query2 = f"""
        다음 CRM 데이터를 통계적으로 분석해주세요: {csv_file}

        다음 분석을 수행해주세요:
        1. 실험군 vs 대조군 전환율 비교 분석
        2. 퍼널별 성과 분석
        3. 채널별 성과 분석
        4. 퍼널별 문구 효과성 분석
        5. 퍼널별 문구 패턴 분석

        각 분석마다 도구를 사용해서 실제 통계 분석을 수행해주세요.
        """
        
        context_info = f"""
        이전 {first_agent} Agent의 분석 결과:
        - 데이터 구조: {context.data_info if context.data_info else "아직 분석 중"}
        - 분석 계획: {context.analysis_plan if context.analysis_plan else "아직 분석 중"}
        """
        
        await run_agent_with_llm(statistical_analyst_agent, query2, "statistical_analysis", context_info)
    
    print(f"\n✅ {first_agent} → {second_agent} Agent 테스트 완료!")
    print("=" * 50)

async def run_triple_agent_test(first_agent: str, second_agent: str, third_agent: str):
    """세 Agent 연속 테스트"""
    print(f"\n🔍 {first_agent} → {second_agent} → {third_agent} Agent 연속 테스트 시작")
    print("=" * 50)
    
    csv_file = DEFAULT_CSV_FILE
    
    # 첫 번째 Agent 실행
    if first_agent == "statistical_analysis":
        query1 = f"""
        다음 CRM 데이터를 통계적으로 분석해주세요: {csv_file}

        다음 분석을 수행해주세요:
        1. 실험군 vs 대조군 전환율 비교 분석
        2. 퍼널별 성과 분석
        3. 채널별 성과 분석
        4. 퍼널별 문구 효과성 분석
        5. 퍼널별 문구 패턴 분석

        각 분석마다 도구를 사용해서 실제 통계 분석을 수행해주세요.
        """
        await run_agent_with_llm(statistical_analyst_agent, query1, "statistical_analysis")
    
    # 두 번째 Agent 실행
    if second_agent == "comprehensive_analysis":
        query2 = f"""
        이전 Agent들의 모든 분석 결과를 종합하여 최종 보고서를 생성해주세요: {csv_file}

        다음 작업을 수행해주세요:
        1. 이전 Agent들의 모든 분석 결과를 종합 검토
        2. 통계적 분석과 LLM 분석 결과의 교차 검증
        3. 비즈니스 관점에서의 종합적 인사이트 도출
        4. 실행 가능한 추천사항 및 액션 아이템 제시
        5. DataFrame/JSON 형태의 구조화된 최종 보고서 생성

        Context에서 이전 분석 결과들을 확인하고 통합적인 관점에서 분석해주세요.
        """
        
        context_info = f"""
        이전 {first_agent} Agent의 분석 결과:
        - 퍼널 분석: {context.funnel_analysis if context.funnel_analysis else "아직 분석 중"}
        """
        
        await run_agent_with_llm(comprehensive_agent, query2, "comprehensive_analysis", context_info)
    
    # 세 번째 Agent 실행
    if third_agent == "data_report":
        query3 = f"""
        이전 Agent들의 모든 분석 결과를 표, 그래프, 텍스트로 종합하여 리포트를 생성해주세요: {csv_file}

        다음 작업을 수행해주세요:
        1. 세그먼트별 전환율 표 생성 (퍼널별, 채널별, 문구별)
        2. 전환율 시각화 그래프 생성 (막대그래프, 히스토그램, 비교차트)
        3. 텍스트 분석 결과 리포트 생성 (문구 길이, 이모지, 숫자 사용 등)
        4. 종합 데이터 분석 리포트 생성 (모든 분석 결과 통합)
        5. LLM 분석 프롬프트 튜닝 제안 생성 (수치와 구체적 이유 강화 방안)

        Context에서 이전 분석 결과들을 확인하고 이해하기 쉬운 형태로 리포트를 생성해주세요.
        """
        
        context_info = f"""
        이전 분석 결과들:
        - {first_agent}: {context.funnel_analysis if context.funnel_analysis else "아직 분석 중"}
        - {second_agent}: {context.final_report if context.final_report else "아직 분석 중"}
        """
        
        await run_agent_with_llm(data_report_agent, query3, "data_report", context_info)
    
    print(f"\n✅ {first_agent} → {second_agent} → {third_agent} Agent 테스트 완료!")
    print("=" * 50)

async def run_quadruple_agent_test(first_agent: str, second_agent: str, third_agent: str, fourth_agent: str):
    """네 Agent 연속 테스트"""
    print(f"\n🔍 {first_agent} → {second_agent} → {third_agent} → {fourth_agent} Agent 연속 테스트 시작")
    print("=" * 50)
    
    csv_file = DEFAULT_CSV_FILE
    
    # 첫 번째 Agent 실행
    if first_agent == "data_understanding":
        query1 = f"""
        다음 CSV 파일을 분석해주세요: {csv_file}

        다음 단계를 따라 분석해주세요:
        1. 데이터 구조를 분석하고
        2. 분석 요구사항을 식별하고
        3. 구체적인 분석 계획을 수립하고
        4. 도메인 용어 이해도를 검증하고
        5. 도메인 용어 사전을 조회해주세요

        각 단계마다 도구를 사용해서 실제 분석을 수행해주세요.
        """
        await run_agent_with_llm(data_understanding_agent, query1, "data_understanding")
    
    # 두 번째 Agent 실행
    if second_agent == "statistical_analysis":
        query2 = f"""
        다음 CRM 데이터를 통계적으로 분석해주세요: {csv_file}

        다음 분석을 수행해주세요:
        1. 실험군 vs 대조군 전환율 비교 분석
        2. 퍼널별 성과 분석
        3. 채널별 성과 분석
        4. 퍼널별 문구 효과성 분석
        5. 퍼널별 문구 패턴 분석

        각 분석마다 도구를 사용해서 실제 통계 분석을 수행해주세요.
        """
        
        context_info = f"""
        이전 {first_agent} Agent의 분석 결과:
        - 데이터 구조: {context.data_info if context.data_info else "아직 분석 중"}
        - 분석 계획: {context.analysis_plan if context.analysis_plan else "아직 분석 중"}
        """
        
        await run_agent_with_llm(statistical_analyst_agent, query2, "statistical_analysis", context_info)
    
    # 세 번째 Agent 실행
    if third_agent == "comprehensive_analysis":
        query3 = f"""
        이전 Agent들의 모든 분석 결과를 종합하여 최종 보고서를 생성해주세요: {csv_file}

        다음 작업을 수행해주세요:
        1. 이전 Agent들의 모든 분석 결과를 종합 검토
        2. 통계적 분석과 LLM 분석 결과의 교차 검증
        3. 비즈니스 관점에서의 종합적 인사이트 도출
        4. 실행 가능한 추천사항 및 액션 아이템 제시
        5. DataFrame/JSON 형태의 구조화된 최종 보고서 생성

        Context에서 이전 분석 결과들을 확인하고 통합적인 관점에서 분석해주세요.
        """
        
        context_info = f"""
        이전 분석 결과들:
        - {first_agent}: {context.data_info if context.data_info else "아직 분석 중"}
        - {second_agent}: {context.funnel_analysis if context.funnel_analysis else "아직 분석 중"}
        """
        
        await run_agent_with_llm(comprehensive_agent, query3, "comprehensive_analysis", context_info)
    
    # 네 번째 Agent 실행
    if fourth_agent == "data_report":
        query4 = f"""
        이전 Agent들의 모든 분석 결과를 표, 그래프, 텍스트로 종합하여 리포트를 생성해주세요: {csv_file}

        다음 작업을 수행해주세요:
        1. 세그먼트별 전환율 표 생성 (퍼널별, 채널별, 문구별)
        2. 전환율 시각화 그래프 생성 (막대그래프, 히스토그램, 비교차트)
        3. 텍스트 분석 결과 리포트 생성 (문구 길이, 이모지, 숫자 사용 등)
        4. 종합 데이터 분석 리포트 생성 (모든 분석 결과 통합)
        5. LLM 분석 프롬프트 튜닝 제안 생성 (수치와 구체적 이유 강화 방안)

        Context에서 이전 분석 결과들을 확인하고 이해하기 쉬운 형태로 리포트를 생성해주세요.
        """
        
        context_info = f"""
        전체 분석 결과들:
        - {first_agent}: {context.data_info if context.data_info else "아직 분석 중"}
        - {second_agent}: {context.funnel_analysis if context.funnel_analysis else "아직 분석 중"}
        - {third_agent}: {context.final_report if context.final_report else "아직 분석 중"}
        """
        
        await run_agent_with_llm(data_report_agent, query4, "data_report", context_info)
    
    print(f"\n✅ {first_agent} → {second_agent} → {third_agent} → {fourth_agent} Agent 테스트 완료!")
    print("=" * 50)

async def run_html_report_test():
    """HTML 보고서만 테스트하는 함수"""
    print("📄 HTML 보고서 생성 테스트")
    print("=" * 50)
    
    csv_file = DEFAULT_CSV_FILE
    
    try:
        # 데이터 로드
        df = pd.read_csv(csv_file)
        print(f"✅ 데이터 로드 완료: {len(df)}행")
        
        # 가짜 Agent 결과 생성 (테스트용)
        agent_results = {
            'data_understanding': "데이터 이해 분석 결과 (테스트용)",
            'statistical_analysis': "통계 분석 결과 (테스트용)",
            'llm_analysis': "LLM 분석 결과 (테스트용)",
            'comprehensive_analysis': "종합 분석 결과 (테스트용)"
        }
        
        # HTML 보고서 생성
        from core.reporting.comprehensive_html_report import create_comprehensive_html_report
        report_path = create_comprehensive_html_report(csv_file, agent_results)
        
        print(f"✅ HTML 보고서 생성 완료: {report_path}")
        print(f"📂 파일 위치: {os.path.abspath(report_path)}")
        
    except Exception as e:
        print(f"❌ 오류 발생: {str(e)}")
        import traceback
        traceback.print_exc()

async def run_category_analysis_test():
    """Category Analysis Agent만 테스트하는 함수"""
    print("🏷️ Category Analysis Agent 테스트")
    print("=" * 50)
    
    csv_file = DEFAULT_CSV_FILE
    
    try:
        # 데이터 로드
        df = pd.read_csv(csv_file)
        print(f"✅ 데이터 로드 완료: {len(df)}행")
        
        # Category Analysis Agent 실행
        category_query = f"""
        다음 CRM 데이터를 카테고리별로 분석해주세요: {csv_file}

        다음 분석을 수행해주세요:
        1. 목적과 문구 텍스트를 분석하여 핵심 카테고리를 3-5개로 분류
        2. 각 카테고리별 Lift 성과를 분석 (Lift = 실험군 전환율 - 대조군 전환율)
        3. 카테고리별 핵심 특징 및 성공 요인 분석
        4. 경영진이 이해하기 쉬운 표 형태로 결과 제시

        각 분석마다 도구를 사용해서 실제 카테고리 분석을 수행해주세요.
        """
        
        await run_agent_with_llm(category_analysis_agent, category_query, "category_analysis")
        
        print(f"✅ Category Analysis Agent 테스트 완료!")
        
    except Exception as e:
        print(f"❌ 오류 발생: {str(e)}")
        import traceback
        traceback.print_exc()

async def run_funnel_segment_test():
    """Funnel Segment Analysis Agent만 테스트하는 함수"""
    print("🎯 Funnel Segment Analysis Agent 테스트")
    print("=" * 50)
    
    csv_file = DEFAULT_CSV_FILE
    
    try:
        # 데이터 로드
        df = pd.read_csv(csv_file)
        print(f"✅ 데이터 로드 완료: {len(df)}행")
        
        # Funnel Segment Analysis Agent 실행
        segment_query = f"""
        다음 CRM 데이터를 퍼널별 세그먼트로 분석해주세요: {csv_file}

        다음 분석을 수행해주세요:
        1. 각 퍼널의 Lift 기준으로 상위/중위/하위 그룹 분류
        2. 그룹별 성공 문구 패턴 및 키워드 도출
        3. 각 그룹에 맞는 맞춤형 메시지 전략 제안
        4. 퍼널별 최적화 권장사항 제시

        각 분석마다 도구를 사용해서 실제 세그먼트 분석을 수행해주세요.
        """
        
        await run_agent_with_llm(funnel_segment_agent, segment_query, "funnel_segment_analysis")
        
        print(f"✅ Funnel Segment Analysis Agent 테스트 완료!")
        
    except Exception as e:
        print(f"❌ 오류 발생: {str(e)}")
        import traceback
        traceback.print_exc()

async def run_funnel_message_analysis_with_report():
    """퍼널별 분석 → 문구 분석 → 레포트 생성 (분할 실행)"""
    print("🚀 퍼널별 문구 분석 시스템 시작 (분할 실행)")
    print("=" * 80)
    
    csv_file = DEFAULT_CSV_FILE
    
    try:
        # 1. Funnel Strategy Agent 실행 (퍼널별 분위수 분석)
        print("\n💡 1단계: Funnel Strategy Agent 실행 (퍼널별 분위수 분석)...")
        strategy_query = f"""
        다음 CRM 데이터의 퍼널별 메시지 전략을 제안해주세요: {csv_file}

        다음 분석을 수행해주세요:
        1. prepare_funnel_quantile_data 도구를 사용해서 분위수 데이터를 준비
        2. 각 그룹의 실제 문구와 Lift 수치를 기반으로 분석
        3. 그룹별 메시지 전략, 메시지 패턴, 공통 특징, 구체적 제안, 핵심 키워드, 성공 사례 도출
        4. 퍼널별 가장 효과적인 문구와 전환율 추출 (수치 포함)

        **중요**: 결과는 반드시 JSON 형식으로 출력하세요.
        {{
          "high_performance_group": {{"strategy": "...", "message_pattern": "...", ...}},
          "medium_performance_group": {{...}},
          "low_performance_group": {{...}}
        }}
        """
        await run_agent_with_llm(funnel_strategy_agent, strategy_query, "funnel_strategy_analysis")
        
        # 2. Statistical Analysis Agent 실행 (퍼널별 통계 분석)
        print("\n📈 2단계: Statistical Analysis Agent 실행 (퍼널별 통계)...")
        statistical_query = f"""
        다음 CRM 데이터를 통계적으로 분석해주세요: {csv_file}

        다음 분석을 수행해주세요:
        1. 실험군 vs 대조군 전환율 비교 분석 (Lift 분석)
        2. 퍼널별 성과 분석 (Lift 기준)
        3. 채널별 성과 분석 (Lift 기준)
        4. 퍼널별 문구 효과성 분석 (Lift 기준)

        각 분석마다 도구를 사용해서 실제 통계 분석을 수행해주세요.
        """
        
        context_info = f"""
        이전 분석 결과들:
        
        Funnel Strategy Agent 결과:
        - 퍼널별 메시지 전략 제안: {context.funnel_strategy_analysis if hasattr(context, 'funnel_strategy_analysis') and context.funnel_strategy_analysis else "아직 분석 중"}
        """
        
        await run_agent_with_llm(statistical_analyst_agent, statistical_query, "statistical_analysis", context_info)
        
        # 3. LLM Analysis Agent 실행 (문구 분석)
        print("\n🤖 3단계: LLM Analysis Agent 실행 (문구 분석)...")
        # Step 3: LLM 프롬프팅 개선 (간결한 출력)
        llm_query = f"""
        다음 CRM 문구들을 LLM으로 의미적으로 분석해주세요: {csv_file}

        **중요: 경영진 보고용으로 간결하고 핵심적인 내용만 출력해주세요.**

        다음 분석을 수행해주세요:
        1. 문장 구조 분석 (길이, 복잡도, 유형, 흐름)
        2. 핵심 키워드 분석 (Lift 기여 단어)
        3. 톤앤매너 분석 (전체 톤, 감정적 어필, 거리감)
        4. 채널별 톤앤매너 분석 (인앱, 푸시, SMS)
        5. 전환율 기여 요소 분석 (상위/하위 문구 특징)
        
        **제외할 섹션:**
        - 퍼널별 적합성 평가 (너무 디테일함)
        - 문구 효과성 이유 분석 (불필요함)

        **출력 형식 요구사항:**
        - 각 섹션별로 명확하게 구분하여 작성 (구분선 사용 금지)
        - 핵심 정보는 불릿 포인트(•)로 정리
        - 수치는 명확하게 표시 (예: "평균 2.4문장", "전환율 31.2%")
        - 예시는 따옴표로 구분하여 제시
        - **간결성**: 각 섹션당 최대 5-6개 불릿 포인트로 제한
        - **핵심만**: 가장 중요한 인사이트와 수치만 포함
        - 경영진이 30초 내에 핵심을 파악할 수 있도록 작성
        - **중요**: 구분선(─, -, =) 사용하지 말고 이모지와 제목으로만 구분

        각 분석마다 도구를 사용해서 실제 LLM 분석을 수행해주세요.
        """
        
        context_info = f"""
        이전 분석 결과들:
        
        Funnel Strategy Agent 결과:
        - 퍼널별 메시지 전략 제안: {context.funnel_strategy_analysis if hasattr(context, 'funnel_strategy_analysis') and context.funnel_strategy_analysis else "아직 분석 중"}
        
        Statistical Analysis Agent 결과:
        - 퍼널 분석: {context.funnel_analysis if context.funnel_analysis else "아직 분석 중"}
        """
        
        await run_agent_with_llm(llm_analyst_agent, llm_query, "llm_analysis", context_info)
        
        # structured_llm_analysis 참조하지 않음 - 원본 llm_analysis만 사용
        
        # 4. Comprehensive Agent 실행 (LLM 분석 결과 구조화)
        print("\n🎯 4단계: Comprehensive Agent 실행 (LLM 분석 결과 구조화)...")
        comprehensive_query = f"""
        이전 Agent들의 분석 결과를 종합하고, LLM 분석 결과를 HTML 규격에 맞게 구조화해주세요: {csv_file}

        **필수 작업**:
        1. structure_llm_analysis_for_html("{csv_file}", "LLM Analysis 결과") 도구를 반드시 호출
        2. 문장 구조, 핵심 키워드, 톤앤매너, 채널별 분석, 전환율 기여 요소를 구조화
        3. JSON 형태의 구조화된 결과 생성

        이전 분석 결과들을 참고하여 종합적인 인사이트를 도출하되,
        반드시 structure_llm_analysis_for_html 도구를 호출하여 HTML 규격에 맞는 데이터를 생성하세요.
        """
        
        comprehensive_context = f"""
        전체 분석 결과들:
        
        Funnel Strategy Agent 결과:
        - 퍼널별 메시지 전략: {context.funnel_strategy_analysis if hasattr(context, 'funnel_strategy_analysis') and context.funnel_strategy_analysis else "아직 분석 중"}
        
        Statistical Analysis Agent 결과:
        - 퍼널 분석: {context.funnel_analysis if context.funnel_analysis else "아직 분석 중"}
        
        LLM Analysis Agent 결과:
        - 메시지 분석: {context.message_analysis if context.message_analysis else "아직 분석 중"}
        """
        
        await run_agent_with_llm(comprehensive_agent, comprehensive_query, "comprehensive_analysis", comprehensive_context)
        
        # 5. HTML 보고서 생성
        print("\n📄 5단계: HTML 보고서 생성...")
        try:
            from core.reporting.comprehensive_html_report import ComprehensiveHTMLReportGenerator
            
            # Agent 결과들을 딕셔너리로 정리
            agent_results = {
                'funnel_strategy_analysis': context.funnel_strategy_analysis if hasattr(context, 'funnel_strategy_analysis') and context.funnel_strategy_analysis else "분석 중",
                'statistical_analysis': context.funnel_analysis if context.funnel_analysis else "분석 중",
                'llm_analysis': context.llm_analysis if hasattr(context, 'llm_analysis') and context.llm_analysis else "분석 중",
                'structured_llm_analysis': "분석 중"  # 참조하지 않음
            }
            
            # 새로운 경영진용 2박스 구조 보고서 생성
            new_report_generator = ComprehensiveHTMLReportGenerator(csv_file)
            new_report_generator.set_agent_results(agent_results)  # Agent 결과 설정
            new_report_content = new_report_generator.generate_new_executive_report()
            
            # 새로운 보고서 저장
            from datetime import datetime
            today = datetime.now().strftime('%Y%m%d')
            reports_dir = f"outputs/reports/{today}"
            os.makedirs(reports_dir, exist_ok=True)
            new_report_path = f"{reports_dir}/{datetime.now().strftime('%y%m%d_%H%M')}_funnel_message_analysis_report.html"
            
            with open(new_report_path, 'w', encoding='utf-8') as f:
                f.write(new_report_content)
            
            print(f"✅ 퍼널별 문구 분석 보고서 생성 완료: {new_report_path}")
            
        except Exception as e:
            print(f"❌ HTML 보고서 생성 오류: {str(e)}")
            import traceback
            traceback.print_exc()
        
        print("\n✅ 퍼널별 문구 분석 시스템 완료!")
        print("=" * 80)
        
    except Exception as e:
        print(f"❌ 오류 발생: {str(e)}")
        import traceback
        traceback.print_exc()

def main():
    """메인 실행 함수"""
    print("🚀 쏘카 CRM 데이터 분석 시스템 (Lift 기반)")
    print("=" * 80)
    print("실행 옵션을 선택하세요:")
    print("1. 종합 분석 시스템 실행 (Lift 기반 경영진용 보고서 포함)")
    print("2. 단일 Agent 테스트 (다양한 조합 선택 가능)")
    print("3. HTML 보고서만 테스트 (빠른 보고서 생성)")
    print("4. Category Analysis Agent 테스트 (카테고리 분류)")
    print("5. Funnel Segment Analysis Agent 테스트 (퍼널 세그먼트 분석)")
    print("6. 퍼널별 문구 분석 → 레포트 생성 (분할 실행) ⭐")
    print("7. 종료")
    
    while True:
        try:
            choice = input("\n선택하세요 (1-7): ").strip()
            
            if choice == "1":
                print("\n🔄 종합 분석 시스템을 실행합니다...")
                asyncio.run(run_comprehensive_analysis())
                break
            elif choice == "2":
                print("\n🔄 단일 Agent 테스트를 실행합니다...")
                asyncio.run(run_agent_test())
                break
            elif choice == "3":
                print("\n🔄 HTML 보고서만 테스트를 실행합니다...")
                asyncio.run(run_html_report_test())
                break
            elif choice == "4":
                print("\n🔄 Category Analysis Agent 테스트를 실행합니다...")
                asyncio.run(run_category_analysis_test())
                break
            elif choice == "5":
                print("\n🔄 Funnel Segment Analysis Agent 테스트를 실행합니다...")
                asyncio.run(run_funnel_segment_test())
                break
            elif choice == "6":
                print("\n🔄 퍼널별 문구 분석 → 레포트 생성을 실행합니다...")
                asyncio.run(run_funnel_message_analysis_with_report())
                break
            elif choice == "7":
                print("👋 프로그램을 종료합니다.")
                break
            else:
                print("❌ 잘못된 선택입니다. 1-7 중에서 선택해주세요.")
        except KeyboardInterrupt:
            print("\n👋 프로그램을 종료합니다.")
            break
        except Exception as e:
            print(f"❌ 오류가 발생했습니다: {str(e)}")
            break

if __name__ == "__main__":
    main()
