"""
Agent Manager - 모든 Agent들을 중앙에서 관리하는 클래스
"""

import asyncio
from typing import Dict, Any
from src.agents.data_understanding_agent import DataUnderstandingAgent
from src.agents.statistical_analysis_agent import StatisticalAnalysisAgent
from src.utils.context_manager import AnalysisContext
from src.utils.agent_runner import AgentRunner

class AgentManager:
    """Agent들을 중앙에서 관리하는 클래스"""
    
    def __init__(self, azure_llm):
        """Agent Manager 초기화"""
        self.azure_llm = azure_llm
        self.runner = AgentRunner()
        
        # Agent 인스턴스들 초기화
        self.data_understanding_agent = DataUnderstandingAgent(azure_llm)
        self.statistical_analysis_agent = StatisticalAnalysisAgent(azure_llm)
    
    async def run_data_understanding(self, csv_file: str, context: AnalysisContext):
        """Data Understanding Agent 실행"""
        print("🤖 data_understanding Agent 실행 중...")
        
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
        
        result = await self.runner.run_agent_with_llm(
            self.data_understanding_agent.agent, 
            query, 
            "data_understanding"
        )
        
        print("✅ data_understanding 완료")
        return result
    
    async def run_statistical_analysis(self, csv_file: str, context: AnalysisContext):
        """Statistical Analysis Agent 실행"""
        print("🤖 statistical_analysis Agent 실행 중...")
        
        query = f"""
        다음 CRM 데이터를 통계적으로 분석해주세요: {csv_file}

        다음 분석을 수행해주세요:
        1. 실험군 vs 대조군 전환율 비교 분석
        2. 퍼널별 성과 분석
        3. 채널별 성과 분석
        4. 소재별 성과 분석
        5. 타겟별 성과 분석
        6. 설정시간/리드타임별 성과 분석
        7. 퍼널별 문구 효과성 분석
        8. 퍼널별 문구 패턴 분석

        각 분석마다 도구를 사용해서 실제 통계 분석을 수행해주세요.
        """
        
        result = await self.runner.run_agent_with_llm(
            self.statistical_analysis_agent.agent, 
            query, 
            "statistical_analysis"
        )
        
        print("✅ statistical_analysis 완료")
        return result
    
    async def run_llm_analysis(self, csv_file: str, context: AnalysisContext):
        """LLM Analysis Agent 실행"""
        print("🤖 llm_analysis Agent 실행 중...")
        
        query = f"""
        다음 CRM 데이터를 LLM으로 분석해주세요: {csv_file}

        다음 분석을 수행해주세요:
        1. 문구별 효과성 LLM 분석
        2. 퍼널별 문구 효과성 분석
        3. 문구 효과성 이유 분석
        4. 문구 패턴 및 키워드 분석
        5. 문구 개선 제안

        각 분석마다 도구를 사용해서 실제 LLM 분석을 수행해주세요.
        """
        
        result = await self.runner.run_agent_with_llm(
            self.llm_analysis_agent.agent, 
            query, 
            "llm_analysis"
        )
        
        print("✅ llm_analysis 완료")
        return result
    
    async def run_comprehensive_analysis(self, csv_file: str, context: AnalysisContext):
        """Comprehensive Agent 실행"""
        print("🤖 comprehensive_analysis Agent 실행 중...")
        
        query = f"""
        다음 CRM 데이터를 종합적으로 분석해주세요: {csv_file}

        다음 분석을 수행해주세요:
        1. 전체 분석 결과 종합
        2. 핵심 인사이트 도출
        3. 실행 가능한 추천사항 제시
        4. 비즈니스 임팩트 평가
        5. 향후 개선 방향 제안

        각 작업마다 도구를 사용해서 실제 종합 분석을 수행해주세요.
        """
        
        result = await self.runner.run_agent_with_llm(
            self.comprehensive_agent.agent, 
            query, 
            "comprehensive_analysis"
        )
        
        print("✅ comprehensive_analysis 완료")
        return result
    
    async def run_data_report(self, csv_file: str, context: AnalysisContext):
        """Data Report Agent 실행"""
        print("🤖 data_report_analysis Agent 실행 중...")
        
        query = f"""
        다음 CRM 데이터 분석 결과를 보고서로 작성해주세요: {csv_file}

        다음 작업을 수행해주세요:
        1. 데이터 분석 보고서 생성
        2. 시각화 차트 생성
        3. 핵심 지표 테이블 생성
        4. 실행 요약 작성
        5. HTML 보고서 생성

        각 작업마다 도구를 사용해서 실제 리포트를 생성해주세요.
        """
        
        result = await self.runner.run_agent_with_llm(
            self.data_report_agent.agent, 
            query, 
            "data_report_analysis"
        )
        
        print("✅ data_report_analysis 완료")
        return result
    
    async def run_criticizer(self, csv_file: str, context: AnalysisContext):
        """Criticizer Agent 실행"""
        print("🤖 criticizer_analysis Agent 실행 중...")
        
        query = f"""
        다음 CRM 데이터 분석 결과를 비판적으로 검토해주세요: {csv_file}

        다음 검토를 수행해주세요:
        1. 분석 방법론 검증
        2. 결과의 신뢰성 평가
        3. 누락된 분석 요소 식별
        4. 개선 제안사항 도출
        5. 최종 평가 보고서 작성

        각 작업마다 도구를 사용해서 실제 비판적 분석을 수행해주세요.
        """
        
        result = await self.runner.run_agent_with_llm(
            self.criticizer_agent.agent, 
            query, 
            "criticizer_analysis"
        )
        
        print("✅ criticizer_analysis 완료")
        return result
