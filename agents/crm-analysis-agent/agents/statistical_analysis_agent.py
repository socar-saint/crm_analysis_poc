"""
Statistical Analysis Agent - 통계적 분석을 담당하는 Agent
"""

from google.adk.agents import Agent
from src.tools.statistical_analysis_tools import (
    analyze_conversion_performance_tool,
    analyze_message_effectiveness_tool,
    analyze_funnel_performance_tool,
    analyze_funnel_message_effectiveness_tool,
    analyze_message_patterns_by_funnel_tool
)
from src.prompts.statistical_analysis_prompts import get_statistical_analysis_prompt
from config.column_descriptions import COLUMN_DESCRIPTIONS

class StatisticalAnalysisAgent:
    """통계적 분석을 담당하는 Agent 클래스"""
    
    def __init__(self, azure_llm):
        """Statistical Analysis Agent 초기화"""
        self.azure_llm = azure_llm
        self.agent = self._create_agent()
    
    def _create_agent(self) -> Agent:
        """Agent 인스턴스 생성"""
        return Agent(
            name="statistical_analyst_agent",
            model=self.azure_llm,
            description="통계 기반 CRM 캠페인 성과를 분석하는 전문가입니다.",
            instruction=get_statistical_analysis_prompt(),
            tools=[
                analyze_conversion_performance_tool,
                analyze_message_effectiveness_tool,
                analyze_funnel_performance_tool,
                analyze_funnel_message_effectiveness_tool,
                analyze_message_patterns_by_funnel_tool
            ]
        )
