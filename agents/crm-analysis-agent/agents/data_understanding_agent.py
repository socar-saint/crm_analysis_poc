"""
Data Understanding Agent - 데이터 구조 분석 및 이해를 담당하는 Agent
"""

from google.adk.agents import Agent
from src.tools.data_analysis_tools import (
    analyze_data_structure,
    identify_analysis_requirements,
    create_analysis_plan
)
from src.tools.domain_tools import (
    verify_domain_understanding,
    get_domain_glossary
)
from src.prompts.data_understanding_prompts import get_data_understanding_prompt
from config.column_descriptions import COLUMN_DESCRIPTIONS

class DataUnderstandingAgent:
    """데이터 이해를 담당하는 Agent 클래스"""
    
    def __init__(self, azure_llm):
        """Data Understanding Agent 초기화"""
        self.azure_llm = azure_llm
        self.agent = self._create_agent()
    
    def _create_agent(self) -> Agent:
        """Agent 인스턴스 생성"""
        return Agent(
            name="data_understanding_agent",
            model=self.azure_llm,
            description="데이터 구조를 분석하고 분석 요구사항을 식별하는 전문가입니다.",
            instruction=get_data_understanding_prompt(),
            tools=[
                analyze_data_structure,
                identify_analysis_requirements,
                create_analysis_plan,
                verify_domain_understanding,
                get_domain_glossary
            ]
        )
