"""
종합적인 HTML 데이터 분석 리포트 생성기 - 2박스 구조
"""

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from datetime import datetime
import json
import os
from typing import Dict, Any, List
import warnings
warnings.filterwarnings('ignore')

# 날짜시간 prefix 생성 함수
def get_datetime_prefix():
    """YYMMDD_HHMM 형식의 날짜시간 prefix 생성"""
    now = datetime.now()
    return now.strftime("%y%m%d_%H%M")

class ComprehensiveHTMLReportGenerator:
    def __init__(self, csv_file_path: str):
        self.csv_file_path = csv_file_path
        self.df = None
        self.agent_results = {}
        
    def load_data(self):
        """CSV 데이터 로드"""
        try:
            self.df = pd.read_csv(self.csv_file_path)
            print(f"✅ 데이터 로드 완료: {len(self.df)}행 x {len(self.df.columns)}열")
        except Exception as e:
            print(f"❌ 데이터 로드 오류: {str(e)}")
            self.df = pd.DataFrame()
        
    def set_agent_results(self, agent_results: Dict[str, Any]):
        """Agent 결과 설정"""
        self.agent_results = agent_results
    
    def _calculate_core_metrics(self) -> Dict[str, Any]:
        """핵심 지표 동적 계산"""
        if self.df is None or len(self.df) == 0:
            return {
                'experiment_conversion_rate': 0,
                'average_lift': 0,
                'experiment_conversions': 0,
                'total_sent': 0
            }
        
        try:
            # 전체 데이터 집계
            total_experiment_conversions = self.df['실험군_1일이내_예약생성'].sum() if '실험군_1일이내_예약생성' in self.df.columns else 0
            total_experiment_sent = self.df['실험군_발송'].sum() if '실험군_발송' in self.df.columns else 0
            total_control_conversions = self.df['대조군_1일이내_예약생성'].sum() if '대조군_1일이내_예약생성' in self.df.columns else 0
            total_control_sent = self.df['대조군_발송'].sum() if '대조군_발송' in self.df.columns else 0
            
            # 전환율 계산 (올바른 공식)
            # 실험군 전환율 = (실험군 전환 유저 숫자 / 실험군 전체 발송) * 100
            experiment_conversion_rate = (total_experiment_conversions / total_experiment_sent * 100) if total_experiment_sent > 0 else 0
            # 대조군 전환율 = (대조군 전환 유저 숫자 / 대조군 전체 발송) * 100
            control_rate = (total_control_conversions / total_control_sent * 100) if total_control_sent > 0 else 0
            # 평균 Lift = 실험군 전환율 - 대조군 전환율
            average_lift = experiment_conversion_rate - control_rate
            
            # 디버깅 정보 출력
            print(f"🔍 핵심 지표 계산: 실험군 {experiment_conversion_rate:.1f}% - 대조군 {control_rate:.1f}% = {average_lift:+.1f}%p")
            
            return {
                'experiment_conversion_rate': round(experiment_conversion_rate, 1),
                'average_lift': round(average_lift, 1),
                'experiment_conversions': total_experiment_conversions,
                'total_sent': total_experiment_sent
            }
        except Exception as e:
            print(f"⚠️ 핵심 지표 계산 오류: {str(e)}")
            return {
                'experiment_conversion_rate': 0,
                'average_lift': 0,
                'experiment_conversions': 0,
                'total_sent': 0
            }
    
    def _generate_funnel_analysis(self) -> str:
        """퍼널별 분석 동적 생성"""
        if self.df is None or len(self.df) == 0:
            return "<p>데이터가 없습니다.</p>"
        
        try:
            # 퍼널별 그룹화 및 분석
            if '퍼널' not in self.df.columns:
                return "<p>퍼널 데이터가 없습니다.</p>"
            
            funnel_stats = []
            # nan 값 제거하고 유효한 퍼널만 처리
            valid_funnels = self.df['퍼널'].dropna().unique()
            for funnel in valid_funnels:
                funnel_data = self.df[self.df['퍼널'] == funnel]
                
                exp_conversions = funnel_data['실험군_1일이내_예약생성'].sum() if '실험군_1일이내_예약생성' in funnel_data.columns else 0
                exp_sent = funnel_data['실험군_발송'].sum() if '실험군_발송' in funnel_data.columns else 0
                ctrl_conversions = funnel_data['대조군_1일이내_예약생성'].sum() if '대조군_1일이내_예약생성' in funnel_data.columns else 0
                ctrl_sent = funnel_data['대조군_발송'].sum() if '대조군_발송' in funnel_data.columns else 0
                
                exp_rate = (exp_conversions / exp_sent * 100) if exp_sent > 0 else 0
                ctrl_rate = (ctrl_conversions / ctrl_sent * 100) if ctrl_sent > 0 else 0
                lift = exp_rate - ctrl_rate
                
                # 성과 등급 결정 (3분위수 기준으로 나중에 계산)
                grade = "pending"
                grade_text = "계산중"
                
                funnel_stats.append({
                    'funnel': funnel,
                    'exp_rate': round(exp_rate, 1),
                    'ctrl_rate': round(ctrl_rate, 1),
                    'lift': round(lift, 1),
                    'campaigns': len(funnel_data),
                    'grade': grade,
                    'grade_text': grade_text
                })
            
            # Lift 기준으로 내림차순 정렬
            funnel_stats.sort(key=lambda x: x['lift'], reverse=True)
            
            # 3분위수 기준으로 등급 재계산
            lifts = [stat['lift'] for stat in funnel_stats]
            q33 = pd.Series(lifts).quantile(0.33)
            q67 = pd.Series(lifts).quantile(0.67)
            
            for stat in funnel_stats:
                if stat['lift'] >= q67:
                    stat['grade'] = "high"
                    stat['grade_text'] = "상위"
                elif stat['lift'] >= q33:
                    stat['grade'] = "medium"
                    stat['grade_text'] = "중위"
                else:
                    stat['grade'] = "low"
                    stat['grade_text'] = "하위"
            
            # HTML 생성
            funnel_html = """
                        <h4>🎯 퍼널별 Lift 성과 분석</h4>
                        <table class="analysis-table">
                            <thead>
                                <tr>
                                    <th>퍼널</th>
                                    <th>실험군 전환율</th>
                                    <th>대조군 전환율</th>
                                    <th>Lift</th>
                                    <th>캠페인 수</th>
                                    <th>성과 등급</th>
                                </tr>
                            </thead>
                            <tbody>
            """
            
            for stat in funnel_stats:
                funnel_html += f"""
                                <tr class="{stat['grade']}">
                                    <td>{stat['funnel']}</td>
                                    <td>{stat['exp_rate']}%</td>
                                    <td>{stat['ctrl_rate']}%</td>
                                    <td>{stat['lift']:+.1f}%p</td>
                                    <td>{stat['campaigns']}개</td>
                                    <td>{stat['grade_text']}</td>
                                </tr>
                """
            
            funnel_html += """
                            </tbody>
                        </table>
            """
            
            return funnel_html
            
        except Exception as e:
            print(f"⚠️ 퍼널별 분석 오류: {str(e)}")
            return "<p>퍼널별 분석 중 오류가 발생했습니다.</p>"
    
    def _extract_llm_sections(self, llm_result) -> Dict[str, str]:
        """LLM 결과에서 섹션별 내용 추출 - 개선된 버전"""
        sections = {
            'sentence_analysis': '',
            'keyword_analysis': '',
            'tone_analysis': '',
            'channel_analysis': '',
            'conversion_analysis': ''
        }
        
        # Handle different types of llm_result
        if isinstance(llm_result, dict):
            # Extract result text from agent result
            result_text = llm_result.get('result', '')
            if isinstance(result_text, dict):
                result_text = result_text.get('result', '')
        else:
            result_text = str(llm_result) if llm_result else ''
        
        if not result_text or result_text == "분석 중":
            return sections
        
        lines = result_text.split('\n')
        current_section = None
        current_content = []
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
                
            # 섹션 시작 감지 (개선된 로직)
            if ('📝' in line and '문장' in line) or '문장 구조 분석' in line:
                if current_section and current_content:
                    sections[current_section] = '\n'.join(current_content)
                current_section = 'sentence_analysis'
                current_content = []
            elif ('🔑' in line and '키워드' in line) or '핵심 키워드 분석' in line:
                if current_section and current_content:
                    sections[current_section] = '\n'.join(current_content)
                current_section = 'keyword_analysis'
                current_content = []
            elif ('🎭' in line and '톤앤매너' in line) or '톤앤매너 분석' in line:
                if current_section and current_content:
                    sections[current_section] = '\n'.join(current_content)
                current_section = 'tone_analysis'
                current_content = []
            elif ('📊' in line and '전환율' in line) or '전환율 기여 요소 분석' in line:
                if current_section and current_content:
                    sections[current_section] = '\n'.join(current_content)
                current_section = 'conversion_analysis'
                current_content = []
            else:
                if current_section:
                    # "Agent 분석 결과 대기 중..." 같은 텍스트는 무시
                    if "Agent 분석 결과 대기 중" not in line and "분석 중" not in line:
                        current_content.append(line)
        
        # 마지막 섹션 저장
        if current_section and current_content:
            sections[current_section] = '\n'.join(current_content)
        
        # 채널별 톤앤매너 섹션은 제거됨
        
        # 전환율 기여 요소가 다른 섹션에 포함된 경우 추출
        if sections['tone_analysis'] and 'Lift 기여 요소 분석' in sections['tone_analysis']:
            tone_content = sections['tone_analysis']
            if 'Lift 기여 요소 분석' in tone_content:
                # Lift 기여 요소 분석 부분을 별도로 추출
                conversion_start = tone_content.find('Lift 기여 요소 분석')
                if conversion_start != -1:
                    conversion_content = tone_content[conversion_start:]
                    # 불필요한 섹션 제거
                    unwanted_sections = ['퍼널별 적합성 평가', '문구 효과성 이유 분석']
                    for unwanted in unwanted_sections:
                        if unwanted in conversion_content:
                            conversion_content = conversion_content.split(unwanted)[0]
                    sections['conversion_analysis'] = conversion_content
        
        # 불필요한 섹션 제거 (모든 섹션에서)
        unwanted_sections = ['퍼널별 적합성 평가', '문구 효과성 이유 분석']
        for section_key in sections:
            if sections[section_key]:
                content = sections[section_key]
                for unwanted in unwanted_sections:
                    if unwanted in content:
                        # 불필요한 섹션 이후의 내용 제거
                        content = content.split(unwanted)[0]
                        sections[section_key] = content.strip()
        
        return sections
    
    def _parse_bullet_points(self, content: str) -> list:
        """• 기반으로 내용을 분리하여 리스트로 반환 - 개선된 버전"""
        try:
            # • 기반으로 분리
            items = []
            
            # 먼저 • 기반으로 분리
            lines = content.split('•')
            
            for line in lines:
                line = line.strip()
                # 구분선과 불필요한 문자들 제거
                if (line and 
                    not line.startswith('---') and 
                    not line.startswith('─') and
                    not line.startswith('=') and
                    not line.startswith('───────────────────────────────') and
                    not line.startswith('──────────────────────────────') and
                    len(line) > 3):  # 너무 짧은 라인 제외
                    
                    # 추가 정리
                    line = line.replace('**', '').replace('*', '')
                    
                    # 하위 항목 처리 (- 기반)
                    if ' - ' in line:
                        # 하위 항목들을 별도로 처리
                        main_item = line.split(' - ')[0].strip()
                        if main_item:
                            items.append(main_item)
                        
                        # 하위 항목들 추가
                        sub_items = line.split(' - ')[1:]
                        for sub_item in sub_items:
                            sub_item = sub_item.strip()
                            if sub_item:
                                items.append(f"  - {sub_item}")
                    else:
                        if line:
                            items.append(line)
            
            # 빈 항목 제거
            items = [item for item in items if item.strip()]
            
            # 최대 8개 항목으로 제한 (가독성 향상)
            if len(items) > 8:
                items = items[:8]
                items.append("... (더 많은 내용은 상세 보고서 참조)")
            
            return items if items else [content]
            
        except Exception as e:
            print(f"⚠️ 불릿 포인트 파싱 오류: {str(e)}")
            return [content]
    
    def _format_llm_content_for_readability(self, content: str) -> str:
        """방안 2: LLM 분석 결과를 경영진 보고용으로 가독성 향상"""
        try:
            # 문장 구조 분석 섹션 개선
            if "문장 구조 분석" in content:
                # 긴 문장을 줄바꿈으로 분리
                content = content.replace(" - ", "\n• ")
                content = content.replace(": ", ":\n• ")
                
                # 예시 문구들을 개별 항목으로 분리
                content = content.replace('"', '\n  "')
                content = content.replace('"', '"\n')
                
                # 수치 정보를 명확하게 구분
                content = content.replace("평균 ", "• 평균 ")
                content = content.replace("범위: ", "• 범위: ")
                content = content.replace("복잡도: ", "• 복잡도: ")
                
            # 핵심 키워드 분석 섹션 개선
            if "핵심 키워드" in content:
                # 키워드별로 개별 항목으로 분리
                content = content.replace("1. ", "\n1. ")
                content = content.replace("2. ", "\n2. ")
                content = content.replace("3. ", "\n3. ")
                content = content.replace("4. ", "\n4. ")
                content = content.replace("5. ", "\n5. ")
                
                # 카테고리별 키워드 구분
                content = content.replace("카테고리별 키워드:", "\n**카테고리별 키워드:**")
                content = content.replace("구체적 예시:", "\n**구체적 예시:**")
                
            # 톤앤매너 분석 섹션 개선
            if "톤앤매너 분석" in content:
                content = content.replace("전체 톤:", "• 전체 톤:")
                content = content.replace("감정적 어필 요소:", "\n• 감정적 어필 요소:")
                content = content.replace("채널별 톤 차이:", "\n• 채널별 톤 차이:")
                
            # 전환율 기여 요소 분석 섹션 개선
            if "전환율 기여 요소" in content:
                content = content.replace("전환율 상위 문구 공통 특징:", "\n**상위 문구 특징:**")
                content = content.replace("하위 문구 문제점:", "\n**하위 문구 문제점:**")
                content = content.replace("효과적 조합:", "\n**효과적 조합:**")
                
                # 번호가 있는 항목들을 개별 줄로 분리
                content = content.replace("1. ", "\n1. ")
                content = content.replace("2. ", "\n2. ")
                content = content.replace("3. ", "\n3. ")
                
            return content
            
        except Exception as e:
            print(f"⚠️ LLM 내용 포맷팅 오류: {str(e)}")
            return content
    
    def _convert_structured_data_to_html(self, data: dict) -> str:
        """구조화된 데이터를 HTML 형태로 변환"""
        html_content = []
        
        # 1. 문장 구조 분석
        if 'sentence_analysis' in data:
            sentence = data['sentence_analysis']
            html_content.append('<p><strong>📝 문장 구조 분석:</strong></p>')
            html_content.append('<ul>')
            html_content.append(f'<li>전체 문장 수: {sentence.get("평균_문장수", "분석 중...")}</li>')
            html_content.append(f'<li>문장 길이: {sentence.get("평균_문장길이", "분석 중...")}</li>')
            html_content.append(f'<li>복잡도: {sentence.get("복잡도", "분석 중...")}</li>')
            html_content.append(f'<li>문장 흐름: {sentence.get("문장흐름", "분석 중...")}</li>')
            html_content.append('</ul>')
        
        # 2. 핵심 키워드 분석
        if 'keyword_analysis' in data:
            html_content.append('<p><strong>🔑 핵심 키워드 분석:</strong></p>')
            html_content.append('<ul>')
            for keyword in data['keyword_analysis']:
                html_content.append(f'<li>{keyword.get("키워드", "")}: {keyword.get("기여도", "")} (전환율 {keyword.get("포함문구전환율", "")})</li>')
            html_content.append('</ul>')
        
        # 3. 톤앤매너 분석
        if 'tone_analysis' in data:
            tone = data['tone_analysis']
            html_content.append('<p><strong>🎭 톤앤매너 분석:</strong></p>')
            html_content.append('<ul>')
            html_content.append(f'<li>전체 톤: {tone.get("전체톤", "분석 중...")}</li>')
            html_content.append(f'<li>친근함: {tone.get("친근함", "분석 중...")}</li>')
            html_content.append(f'<li>긴급성: {tone.get("긴급성", "분석 중...")}</li>')
            html_content.append(f'<li>감정적 어필: {tone.get("감정적어필", "분석 중...")}</li>')
            html_content.append('</ul>')
        
        # 4. 전환율 기여 요소 분석
        if 'contribution_analysis' in data:
            contrib = data['contribution_analysis']
            html_content.append('<p><strong>📊 전환율 기여 요소 분석:</strong></p>')
            html_content.append('<ul>')
            html_content.append('<li><strong>전환율 상위 문구 공통 특징:</strong></li>')
            for feature in contrib.get('상위문구특징', []):
                html_content.append(f'<li>{feature}</li>')
            html_content.append('<li><strong>전환율 하위 문구 공통 문제점:</strong></li>')
            for problem in contrib.get('하위문구문제점', []):
                html_content.append(f'<li>{problem}</li>')
            html_content.append('<li><strong>효과적인 문구 조합:</strong></li>')
            for combo in contrib.get('효과적문구조합', []):
                html_content.append(f'<li>{combo}</li>')
            html_content.append('</ul>')
        
        return '\n'.join(html_content)
    
    def _generate_llm_analysis_content(self) -> str:
        """LLM 분석 내용 동적 생성 - 1719 HTML 구조"""
        # structured_llm_analysis 참조하지 않고 원본 llm_analysis만 사용
        llm_result = self.agent_results.get('llm_analysis', '')
        
        # Handle new structure where llm_result is a dict
        if isinstance(llm_result, dict):
            # Extract the actual result text from the agent result
            result_text = llm_result.get('result', '')
            if isinstance(result_text, dict):
                result_text = result_text.get('result', '')
            llm_result = result_text
        
        if llm_result and llm_result != "분석 중" and llm_result != "Agent 분석 결과 대기 중...":
            # ========================================
            # 방안 선택: 두 방안 중 하나를 선택하세요
            # ========================================
            
            # ========================================
            # 최종 선택: 방안 1 (LLM 프롬프팅 개선)
            # ========================================
            # 방안 1: LLM 프롬프팅 개선 (최종 선택)
            sections = self._extract_llm_sections(llm_result)
            
            # 방안 2: HTML 파싱 개선 (비활성화 - 가독성 문제)
            # formatted_content = self._format_llm_content_for_readability(llm_result)
            # sections = self._extract_llm_sections(formatted_content)
            
            # 문장 구조 분석 - • 기반 구조화
            sentence_analysis = sections.get('sentence_analysis', '')
            if sentence_analysis:
                # • 기반으로 내용을 분리하여 구조화
                sentence_items = self._parse_bullet_points(sentence_analysis)
                sentence_html = f"""
                    <p><strong>📝 문장 구조 분석:</strong></p>
                    <ul>
                        {''.join([f'<li>{item}</li>' for item in sentence_items])}
                    </ul>
                """
            else:
                sentence_html = """
                    <p><strong>📝 문장 구조 분석:</strong></p>
                    <ul>
                        <li>전체 문장 수: 분석 중...</li>
                        <li>문장 길이: 분석 중...</li>
                        <li>복잡도: 분석 중...</li>
                        <li>문장 흐름: 분석 중...</li>
                    </ul>
                """
            
            # 키워드 분석 - • 기반 구조화
            keyword_analysis = sections.get('keyword_analysis', '')
            if keyword_analysis:
                keyword_items = self._parse_bullet_points(keyword_analysis)
                keyword_html = f"""
                    <p><strong>🔑 핵심 키워드 분석:</strong></p>
                    <ul>
                        {''.join([f'<li>{item}</li>' for item in keyword_items])}
                    </ul>
                """
            else:
                keyword_html = """
                    <p><strong>🔑 핵심 키워드 분석:</strong></p>
                    <ul>
                        <li>Agent 분석 결과 대기 중...</li>
                    </ul>
                """
            
            # 톤앤매너 분석 - • 기반 구조화
            tone_analysis = sections.get('tone_analysis', '')
            if tone_analysis:
                tone_items = self._parse_bullet_points(tone_analysis)
                tone_html = f"""
                    <p><strong>🎭 톤앤매너 분석:</strong></p>
                    <ul>
                        {''.join([f'<li>{item}</li>' for item in tone_items])}
                    </ul>
                """
            else:
                tone_html = """
                    <p><strong>🎭 톤앤매너 분석:</strong></p>
                    <ul>
                        <li>전체 톤: 분석 중...</li>
                        <li>친근함: 분석 중...</li>
                        <li>긴급성: 분석 중...</li>
                        <li>감정적 어필: 분석 중...</li>
                    </ul>
                """
            
            # 채널별 톤앤매너 섹션 제거됨
            
            # 전환율 기여 요소 분석 - • 기반 구조화
            conversion_analysis = sections.get('conversion_analysis', '')
            if conversion_analysis:
                conversion_items = self._parse_bullet_points(conversion_analysis)
                conversion_html = f"""
                    <p><strong>📊 전환율 기여 요소 분석:</strong></p>
                    <ul>
                        {''.join([f'<li>{item}</li>' for item in conversion_items])}
                    </ul>
                """
            else:
                conversion_html = """
                    <p><strong>📊 전환율 기여 요소 분석:</strong></p>
                    <ul>
                        <li><strong>전환율 상위 문구 공통 특징:</strong></li>
                        <li>Agent 분석 결과 대기 중...</li>
                        
                        <li><strong>전환율 하위 문구 공통 문제점:</strong></li>
                        <li>Agent 분석 결과 대기 중...</li>
                        
                        <li><strong>효과적인 문구 조합:</strong></li>
                        <li>Agent 분석 결과 대기 중...</li>
                    </ul>
                """
            
            return sentence_html + keyword_html + tone_html + conversion_html
        else:
            return """
                    <p><strong>📝 문장 구조 분석:</strong></p>
                    <ul>
                        <li>전체 문장 수: 분석 중...</li>
                        <li>문장 길이: 분석 중...</li>
                        <li>복잡도: 분석 중...</li>
                        <li>문장 흐름: 분석 중...</li>
                    </ul>
                
                    <p><strong>🔑 핵심 키워드 분석:</strong></p>
                    <ul>
                        <li>Agent 분석 결과 대기 중...</li>
                    </ul>
                
                    <p><strong>🎭 톤앤매너 분석:</strong></p>
                    <ul>
                        <li>전체 톤: 분석 중...</li>
                        <li>친근함: 분석 중...</li>
                        <li>긴급성: 분석 중...</li>
                        <li>감정적 어필: 분석 중...</li>
                    </ul>
                
                    <!-- 채널별 톤앤매너 섹션 제거됨 -->
                
                    <p><strong>📊 전환율 기여 요소 분석:</strong></p>
                    <ul>
                        <li><strong>전환율 상위 문구 공통 특징:</strong></li>
                        <li>Agent 분석 결과 대기 중...</li>
                        
                        <li><strong>전환율 하위 문구 공통 문제점:</strong></li>
                        <li>Agent 분석 결과 대기 중...</li>
                        
                        <li><strong>효과적인 문구 조합:</strong></li>
                        <li>Agent 분석 결과 대기 중...</li>
                    </ul>
            """
    
    def _calculate_keyword_metrics(self) -> List[Dict[str, Any]]:
        """키워드별 지표 계산"""
        if self.df is None or len(self.df) == 0:
            return []
        
        try:
            # 주요 키워드 리스트
            keywords = ['할인', '무료', '즉시', '지금', '쿠폰', '특가', '마감', 'D-DAY', '확정', '예약']
            keyword_metrics = []
            
            for keyword in keywords:
                # 키워드가 포함된 문구들 필터링
                keyword_messages = self.df[self.df['문구'].str.contains(keyword, na=False)]
                
                if len(keyword_messages) > 0:
                    # 키워드별 평균 Lift 계산 (실시간 계산)
                    exp_rate = keyword_messages['실험군_1일이내_예약생성'].sum() / keyword_messages['실험군_발송'].sum() if keyword_messages['실험군_발송'].sum() > 0 else 0
                    ctrl_rate = keyword_messages['대조군_1일이내_예약생성'].sum() / keyword_messages['대조군_발송'].sum() if keyword_messages['대조군_발송'].sum() > 0 else 0
                    avg_lift = exp_rate - ctrl_rate
                    
                    # 키워드별 전환율 계산
                    total_conversions = keyword_messages['실험군_1일이내_예약생성'].sum()
                    total_sent = keyword_messages['실험군_발송'].sum()
                    conversion_rate = (total_conversions / total_sent * 100) if total_sent > 0 else 0
                    
                    # 사용 빈도 계산
                    frequency = len(keyword_messages)
                    if frequency >= 10:
                        freq_level = "높음"
                    elif frequency >= 5:
                        freq_level = "중간"
                    else:
                        freq_level = "낮음"
                    
                    keyword_metrics.append({
                        'keyword': keyword,
                        'avg_lift': round(avg_lift, 1),
                        'conversion_rate': round(conversion_rate, 1),
                        'frequency': freq_level,
                        'count': frequency
                    })
            
            # Lift 기준으로 정렬
            keyword_metrics.sort(key=lambda x: x['avg_lift'], reverse=True)
            return keyword_metrics[:5]  # 상위 5개만 반환
            
        except Exception as e:
            print(f"⚠️ 키워드 지표 계산 오류: {str(e)}")
            return []
    
    def _generate_keyword_analysis(self) -> str:
        """키워드 분석 테이블 동적 생성 - 1719 HTML 구조"""
        keyword_metrics = self._calculate_keyword_metrics()
        
        if not keyword_metrics:
            # 데이터 없음 처리
            return """
            <div class="insight-section">
                <h5>📊 전환율 기여 상위 키워드</h5>
                <table class="analysis-table">
                    <thead>
                        <tr>
                            <th>키워드</th>
                            <th>평균 Lift</th>
                            <th>포함 문구 전환율</th>
                            <th>사용 빈도</th>
                        </tr>
                    </thead>
                    <tbody>
                        <tr>
                            <td colspan="4" style="text-align: center; padding: 20px; color: #666;">
                                키워드 분석 데이터가 없습니다.
                            </td>
                        </tr>
                    </tbody>
                </table>
            </div>
            """
        
        # 동적 데이터로 테이블 생성
        table_html = """
            <div class="insight-section">
                <h5>📊 전환율 기여 상위 키워드</h5>
                <table class="analysis-table">
                    <thead>
                        <tr>
                            <th>키워드</th>
                            <th>평균 Lift</th>
                            <th>포함 문구 전환율</th>
                            <th>사용 빈도</th>
                        </tr>
                    </thead>
                    <tbody>
        """
        
        for metric in keyword_metrics:
            # Lift 값에 따른 클래스 결정
            if metric['avg_lift'] >= 1.0:
                row_class = "high"
            elif metric['avg_lift'] >= 0:
                row_class = "medium"
            else:
                row_class = "low"
            
            table_html += f"""
                        <tr class="{row_class}">
                            <td>{metric['keyword']}</td>
                            <td>{metric['avg_lift']:+.1f}%p</td>
                            <td>{metric['conversion_rate']}%</td>
                            <td>{metric['frequency']}</td>
                        </tr>
            """
        
        table_html += """
                    </tbody>
                </table>
            </div>
        """
        
        return table_html
    
    def _get_top_messages(self) -> List[Dict[str, Any]]:
        """상위 Lift 문구들 추출"""
        if self.df is None or len(self.df) == 0:
            return []
        
        try:
            # Lift 실시간 계산하여 상위 5개 문구 추출
            self.df['Lift_calculated'] = (self.df['실험군_1일이내_예약생성'] / self.df['실험군_발송'] - 
                                        self.df['대조군_1일이내_예약생성'] / self.df['대조군_발송']).fillna(0)
            top_messages = self.df.nlargest(5, 'Lift_calculated')
            
            patterns = []
            for idx, row in top_messages.iterrows():
                message = row.get('문구', '')
                # Lift 실시간 계산
                exp_rate = row['실험군_1일이내_예약생성'] / row['실험군_발송'] if row['실험군_발송'] > 0 else 0
                ctrl_rate = row['대조군_1일이내_예약생성'] / row['대조군_발송'] if row['대조군_발송'] > 0 else 0
                lift = exp_rate - ctrl_rate
                
                # 패턴 타입 결정
                pattern_type = self._analyze_message_pattern(message)
                
                patterns.append({
                    'type': pattern_type,
                    'message': message[:100] + "..." if len(message) > 100 else message,
                    'lift': lift * 100  # 백분율로 변환
                })
            
            return patterns
            
        except Exception as e:
            print(f"⚠️ 상위 문구 추출 오류: {str(e)}")
            return []
    
    def _analyze_message_pattern(self, message: str) -> str:
        """문구 패턴 분석 (더 구체적인 분류)"""
        # 우선순위에 따라 패턴 분류
        if '전기차' in message and '주행요금' in message:
            return "전기차 혜택 패턴"
        elif '할인' in message and ('60%' in message or '65%' in message or '75%' in message):
            return "대폭 할인 패턴"
        elif '지금' in message and ('놓치' in message or '마감' in message):
            return "긴급성 FOMO 패턴"
        elif '지금' in message or '바로' in message or '즉시' in message:
            return "즉시 행동 패턴"
        elif '마감' in message or 'D-DAY' in message or '놓치' in message:
            return "FOMO 패턴"
        elif '#' in message or '님' in message:
            return "개인화 패턴"
        elif '무료' in message or '0원' in message:
            return "무료 혜택 패턴"
        elif '할인' in message:
            return "할인 혜택 패턴"
        else:
            return "일반 안내 패턴"
    
    def _generate_pattern_analysis(self) -> str:
        """문구 패턴 분석 동적 생성 - 1719 HTML 구조"""
        top_patterns = self._get_top_messages()
        
        if not top_patterns:
            # 데이터 없음 처리
            return """
            <div class="insight-section">
                <h5>🎯 효과적 문구 패턴</h5>
                <div class="pattern-grid">
                    <div class="pattern-item" style="text-align: center; padding: 40px; color: #666;">
                        <strong>문구 패턴 분석 데이터가 없습니다.</strong><br>
                        <span>상위 Lift 문구를 찾을 수 없습니다.</span>
                    </div>
                </div>
            </div>
            """
        
        # 동적 데이터로 패턴 그리드 생성
        pattern_html = """
            <div class="insight-section">
                <h5>🎯 효과적 문구 패턴</h5>
                <div class="pattern-grid">
        """
        
        for pattern in top_patterns:
            pattern_html += f"""
                <div class="pattern-item">
                    <strong>{pattern['type']}:</strong><br>
                    "{pattern['message']}"<br>
                    <span class="conversion-rate">Lift: {pattern['lift']:+.1f}%p</span>
                </div>
            """
        
        pattern_html += """
                </div>
            </div>
        """
        
        return pattern_html
    
    def _analyze_tone_effectiveness(self) -> List[Dict[str, str]]:
        """톤앤매너 효과성 분석"""
        if self.df is None or len(self.df) == 0:
            return []
        
        try:
            tone_analysis = []
            
            # 전체 톤 분석
            total_messages = len(self.df)
            emoji_messages = len(self.df[self.df['문구'].str.contains('[😀-🙏]', na=False)])
            name_messages = len(self.df[self.df['문구'].str.contains('#|님', na=False)])
            
            tone_analysis.append({
                'type': '전체 톤',
                'description': f'친근/즉시성/개인화/안내형 – 이모지({emoji_messages}개), #이름({name_messages}개), 특혜 강조가 특징'
            })
            
            # 친근함 분석
            friendly_keywords = ['님', '해주세요', '확정해', '이용해보세요']
            friendly_count = sum([len(self.df[self.df['문구'].str.contains(keyword, na=False)]) for keyword in friendly_keywords])
            
            tone_analysis.append({
                'type': '친근함',
                'description': f'고객 이름, 대화체, 짧은 문장 ("#NAME님", "확정해 주세요") - {friendly_count}개 문구'
            })
            
            # 긴급성 분석
            urgency_keywords = ['지금', '바로', '빠르게', '오늘', '마감']
            urgency_count = sum([len(self.df[self.df['문구'].str.contains(keyword, na=False)]) for keyword in urgency_keywords])
            
            tone_analysis.append({
                'type': '긴급성',
                'description': f'"오늘 지나면", "지금", "빠르게", "예약이 차는 중!" - {urgency_count}개 문구'
            })
            
            # 감정적 어필 분석
            fomo_keywords = ['놓치', '마감', 'D-DAY', '한정']
            fomo_count = sum([len(self.df[self.df['문구'].str.contains(keyword, na=False)]) for keyword in fomo_keywords])
            
            tone_analysis.append({
                'type': '감정적 어필',
                'description': f'FOMO(놓칠까봐 두려움), 희귀성(한정 쿠폰), 사회적 증거 - {fomo_count}개 문구'
            })
            
            return tone_analysis
            
        except Exception as e:
            print(f"⚠️ 톤앤매너 분석 오류: {str(e)}")
            return []
    
    def _generate_tone_effectiveness(self) -> str:
        """톤앤매너 효과성 동적 생성 - 1719 HTML 구조"""
        tone_analysis = self._analyze_tone_effectiveness()
        
        if not tone_analysis:
            # 데이터 없음 처리
            return """
            <div class="insight-section">
                <h5>📈 톤앤매너 효과성</h5>
                <div class="pattern-grid">
                    <div class="pattern-item" style="text-align: center; padding: 40px; color: #666;">
                        <strong>톤앤매너 분석 데이터가 없습니다.</strong><br>
                        <span>메시지 데이터를 분석할 수 없습니다.</span>
                    </div>
                </div>
            </div>
            """
        
        # 동적 데이터로 톤앤매너 그리드 생성
        tone_html = """
            <div class="insight-section">
                <h5>📈 톤앤매너 효과성</h5>
                <div class="pattern-grid">
        """
        
        for tone in tone_analysis:
            tone_html += f"""
                <div class="pattern-item">
                    <strong>{tone['type']}:</strong><br>
                    <span>{tone['description']}</span>
                </div>
            """
        
        tone_html += """
                </div>
            </div>
        """
        
        return tone_html
        
    def generate_new_executive_report(self) -> str:
        """새로운 경영진용 2박스 구조 보고서 생성"""
        try:
            df = pd.read_csv(self.csv_file_path)
            
            # 주차 계산
            from datetime import datetime
            today = datetime.now()
            week_number = today.isocalendar()[1]
            
            # 동적 핵심 지표 계산
            core_metrics = self._calculate_core_metrics()
            
            # 기존 변수들도 유지 (호환성을 위해)
            total_campaigns = len(df)
            total_conversions = core_metrics['experiment_conversions']
            total_sent = core_metrics['total_sent']
            exp_rate = core_metrics['experiment_conversion_rate'] / 100
            total_lift = core_metrics['average_lift'] / 100
            
            # 카테고리별 분석 (Lift 기준)
            category_analysis = ""
            if '목적' in df.columns and '실험군_발송' in df.columns and '실험군_1일이내_예약생성' in df.columns and '대조군_발송' in df.columns and '대조군_1일이내_예약생성' in df.columns:
                jeju_air = df[df['목적'].str.contains('제주|항공', case=False, na=False)]
                electric = df[df['목적'].str.contains('전기차|전기', case=False, na=False)]
                
                # Lift 계산: 실험군 전환율 - 대조군 전환율 (올바른 계산)
                jeju_exp_rate = (jeju_air['실험군_1일이내_예약생성'].sum() / jeju_air['실험군_발송'].sum()) if len(jeju_air) > 0 and jeju_air['실험군_발송'].sum() > 0 else 0
                jeju_ctrl_rate = (jeju_air['대조군_1일이내_예약생성'].sum() / jeju_air['대조군_발송'].sum()) if len(jeju_air) > 0 and jeju_air['대조군_발송'].sum() > 0 else 0
                jeju_lift = jeju_exp_rate - jeju_ctrl_rate
                
                electric_exp_rate = (electric['실험군_1일이내_예약생성'].sum() / electric['실험군_발송'].sum()) if len(electric) > 0 and electric['실험군_발송'].sum() > 0 else 0
                electric_ctrl_rate = (electric['대조군_1일이내_예약생성'].sum() / electric['대조군_발송'].sum()) if len(electric) > 0 and electric['대조군_발송'].sum() > 0 else 0
                electric_lift = electric_exp_rate - electric_ctrl_rate
                
                jeju_conversions = jeju_air['실험군_1일이내_예약생성'].sum() if len(jeju_air) > 0 else 0
                electric_conversions = electric['실험군_1일이내_예약생성'].sum() if len(electric) > 0 else 0
                
                category_analysis = f"""
                <div class="category-performance">
                    <h4>🏷️ 카테고리별 성과 (Lift 기준)</h4>
                    <div class="category-grid">
                        <div class="category-item">
                            <span class="category-name">제주/항공 관련</span>
                            <span class="category-conversions">Lift: +{jeju_lift:.1f}%p ({jeju_conversions:.0f}건)</span>
                        </div>
                        <div class="category-item">
                            <span class="category-name">전기차</span>
                            <span class="category-conversions">Lift: +{electric_lift:.1f}%p ({electric_conversions:.0f}건)</span>
                    </div>
                </div>
                </div>
                """
            
            # 퍼널별 그룹 분석 (Lift 기준)
            funnel_analysis = ""
            if '퍼널' in df.columns and '실험군_발송' in df.columns and '실험군_1일이내_예약생성' in df.columns and '대조군_발송' in df.columns and '대조군_1일이내_예약생성' in df.columns:
                # Lift 계산 (올바른 계산)
                df['exp_rate'] = df['실험군_1일이내_예약생성'] / df['실험군_발송']
                df['ctrl_rate'] = df['대조군_1일이내_예약생성'] / df['대조군_발송']
                df['lift'] = df['exp_rate'] - df['ctrl_rate']
                funnel_stats = df.groupby('퍼널')['lift'].agg(['mean', 'count']).reset_index()
                funnel_stats['lift_pct'] = funnel_stats['mean']
                funnel_stats = funnel_stats.sort_values('lift_pct', ascending=False)
                
                # 3분위수 기준 그룹 분류
                q33 = funnel_stats['lift_pct'].quantile(0.33)
                q67 = funnel_stats['lift_pct'].quantile(0.67)
                
                high_performers = funnel_stats[funnel_stats['lift_pct'] >= q67]
                medium_performers = funnel_stats[(funnel_stats['lift_pct'] >= q33) & (funnel_stats['lift_pct'] < q67)]
                low_performers = funnel_stats[funnel_stats['lift_pct'] < q33]
                
                # 동적 퍼널별 분석 생성
                funnel_table_html = self._generate_funnel_analysis()
                if False:  # 기존 코드 비활성화
                    funnel_table_html = f"""
                    <div class="funnel-analysis-table">
                        <h4>🎯 퍼널별 Lift 성과 분석</h4>
                        <table class="analysis-table">
                            <thead>
                                <tr>
                                    <th>퍼널</th>
                                    <th>실험군 전환율</th>
                                    <th>대조군 전환율</th>
                                    <th>Lift</th>
                                    <th>캠페인 수</th>
                                    <th>성과 등급</th>
                                </tr>
                            </thead>
                            <tbody>
                    """
                    
                    # 3분위수 기준 계산
                    q33 = funnel_stats['lift_pct'].quantile(0.33)
                    q67 = funnel_stats['lift_pct'].quantile(0.67)
                    
                    for _, row in funnel_stats.iterrows():
                        # 성과 등급 결정 (3분위수 기준)
                        if row['lift_pct'] >= q67:
                            grade = "상위"
                            grade_class = "high"
                        elif row['lift_pct'] >= q33:
                            grade = "중위"
                            grade_class = "medium"
                        else:
                            grade = "하위"
                            grade_class = "low"
                        
                        # 실험군/대조군 전환율 계산 (퍼널별 전체 전환율)
                        funnel_data = df[df['퍼널'] == row['퍼널']]
                        exp_rate = funnel_data['실험군_1일이내_예약생성'].sum() / funnel_data['실험군_발송'].sum()
                        ctrl_rate = funnel_data['대조군_1일이내_예약생성'].sum() / funnel_data['대조군_발송'].sum()
                        
                        # 실시간 Lift 계산
                        lift = exp_rate - ctrl_rate
                        
                        funnel_table_html += f"""
                                <tr class="{grade_class}">
                                    <td>{row['퍼널']}</td>
                                    <td>{exp_rate*100:.1f}%</td>
                                    <td>{ctrl_rate*100:.1f}%</td>
                                    <td>{lift*100:+.1f}%p</td>
                                    <td>{int(row['count'])}</td>
                                    <td><span class="grade-badge {grade_class}">{grade}</span></td>
                                </tr>
                        """
                    
                    funnel_table_html += """
                            </tbody>
                        </table>
        </div>
        """
        
                # 퍼널별 메시지 전략 제안 섹션 추가
                strategy_section = ""
                if len(funnel_stats) > 0:
                    # 3분위수 기준 그룹화 (첫 번째 계산과 동일한 기준 사용)
                    q33 = funnel_stats['lift_pct'].quantile(0.33)
                    q67 = funnel_stats['lift_pct'].quantile(0.67)
                    
                    high_group = funnel_stats[funnel_stats['lift_pct'] >= q67]
                    medium_group = funnel_stats[(funnel_stats['lift_pct'] >= q33) & (funnel_stats['lift_pct'] < q67)]
                    low_group = funnel_stats[funnel_stats['lift_pct'] < q33]
                    
                    # Funnel Strategy Agent 결과 파싱
                    strategy_data = {}
                    
                    # 디버깅: Agent 결과 확인
                    print(f"🔍 Agent 결과 디버깅:")
                    print(f"  - self.agent_results 존재: {self.agent_results is not None}")
                    if self.agent_results:
                        print(f"  - Agent 결과 키들: {list(self.agent_results.keys())}")
                        print(f"  - funnel_strategy_analysis 존재: {'funnel_strategy_analysis' in self.agent_results}")
                        if 'funnel_strategy_analysis' in self.agent_results:
                            print(f"  - funnel_strategy_analysis 타입: {type(self.agent_results['funnel_strategy_analysis'])}")
                            print(f"  - funnel_strategy_analysis 내용 (처음 200자): {str(self.agent_results['funnel_strategy_analysis'])[:200]}")
                    
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
                    
                    # 디버깅: 파싱된 strategy_data 확인
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
                    
                    # 그룹별 전략 HTML 생성 함수
                    def generate_group_strategy(group_type, group_df, q_range):
                        group_key = f"{group_type}_performance_group"
                        if strategy_data and group_key in strategy_data:
                            group_info = strategy_data[group_key]
                            
                            # 퍼널 태그 - strategy_data에서 퍼널 목록 추출
                            funnel_names = []
                            if 'funnels' in group_info:
                                funnel_names = [funnel['funnel'] for funnel in group_info['funnels']]
                            else:
                                # fallback: group_df 사용
                                funnel_names = [row["퍼널"] for _, row in group_df.iterrows()]
                            
                            funnel_tags = ''.join([f'<span class="funnel-tag {group_type}">{name}</span>' for name in funnel_names])
                            
                            # 전략 정보 추출 (새로운 JSON 구조)
                            strategy = group_info.get('strategy', '데이터 기반 전략 수립 필요')
                            message_pattern = group_info.get('message_pattern', '패턴 분석 중')
                            common_features = group_info.get('common_features', [])
                            recommendations = group_info.get('recommendations', [])
                            keywords = group_info.get('keywords', [])
                            funnel_top_messages = group_info.get('funnel_top_messages', [])
                            
                            # 퍼널별 최고 성과 문구를 리스트로 포맷팅
                            funnel_msg_list = '<br>'.join([f'• {msg}' for msg in funnel_top_messages]) if funnel_top_messages else '• 분석 중'
                            
                            return f"""
                            <div class="strategy-group {group_type}-group">
                                <h5>{'🎯' if group_type == 'high' else '⚖️' if group_type == 'medium' else '⚠️'} {q_range}</h5>
                                <div class="group-funnels">{funnel_tags}</div>
                                <div class="strategy-recommendation">
                                    <strong>전략:</strong> {strategy}<br>
                                    <strong>메시지 패턴:</strong> {message_pattern}<br>
                                    <strong>공통 특징:</strong> {', '.join(common_features) if common_features else '분석 중'}<br>
                                    <strong>구체적 제안:</strong><br>{('<br>'.join([f'  {i+1}. {rec}' for i, rec in enumerate(recommendations)]) if recommendations else '  분석 중')}<br>
                                    <strong>핵심 키워드:</strong> {', '.join([f'"{k}"' for k in keywords]) if keywords else '분석 중'}<br>
                                    <strong>퍼널별 가장 효과적인 문구 (전환율 포함):</strong><br>{funnel_msg_list}
                    </div>
                </div>
                            """
                        else:
                            # 기본 하드코딩 (Agent 결과 없을 때)
                            funnel_names = [row["퍼널"] for _, row in group_df.iterrows()]
                            funnel_tags = ''.join([f'<span class="funnel-tag {group_type}">{name}</span>' for name in funnel_names])
                            return f"""
                            <div class="strategy-group {group_type}-group">
                                <h5>{'🎯' if group_type == 'high' else '⚖️' if group_type == 'medium' else '⚠️'} {q_range}</h5>
                                <div class="group-funnels">{funnel_tags}</div>
                                <div class="strategy-recommendation">
                                    <strong>전략:</strong> Agent 분석 결과 대기 중<br>
                                    <strong>메시지 패턴:</strong> 분석 중<br>
                                    <strong>공통점:</strong> 분석 중
            </div>
                            </div>
                            """
                    
                    strategy_section = f"""
                    <div class="funnel-strategy-section">
                        <h4>💡 퍼널별 메시지 전략 제안 (3분위수 기준)</h4>
                        <div class="strategy-groups">
                            {generate_group_strategy('high', high_group, '상위 그룹')}
                            {generate_group_strategy('medium', medium_group, '중위 그룹')}
                            {generate_group_strategy('low', low_group, '하위 그룹')}
                    </div>
                </div>
                    """
                
                funnel_analysis = funnel_table_html + strategy_section
            
            # 문구 효과성 분석 (Lift 기준) - 두 번째 박스에서 처리하므로 여기서는 제거
            message_analysis = ""
            
            # Boxplot 시각화 생성
            boxplot_html = ""
            try:
                import matplotlib.pyplot as plt
                import seaborn as sns
                
                if '퍼널' in df.columns and '실험군_예약전환율' in df.columns and '대조군_예약전환율' in df.columns:
                    # Lift 계산이 아직 안되어 있다면 계산
                    if 'lift' not in df.columns:
                        df['lift'] = df['실험군_예약전환율'] - df['대조군_예약전환율']
                    
                    plt.figure(figsize=(12, 8))
                    sns.boxplot(data=df, x='퍼널', y='lift')
                    plt.title('퍼널별 Lift 분포 (Boxplot)', fontsize=14)
                    plt.xlabel('퍼널', fontsize=12)
                    plt.ylabel('Lift (%p)', fontsize=12)
                    plt.xticks(rotation=45)
                    plt.tight_layout()
                    
                    # Boxplot 저장
                    from datetime import datetime
                    today = datetime.now().strftime('%Y%m%d')
                    reports_dir = f"outputs/reports/{today}"
                    os.makedirs(reports_dir, exist_ok=True)
                    boxplot_path = f"{reports_dir}/{datetime.now().strftime('%Y%m%d%H%M')}_funnel_boxplot.png"
                    plt.savefig(boxplot_path, dpi=300, bbox_inches='tight')
                    plt.close()
                    
                    boxplot_html = f"""
                    <div class="boxplot-section">
                        <h4>📊 퍼널별 Lift 분포 분석</h4>
                        <img src="{boxplot_path}" alt="퍼널별 Lift Boxplot" class="boxplot-chart">
                    </div>
                    """
            except Exception as e:
                print(f"Boxplot 생성 오류: {str(e)}")
                boxplot_html = ""
            
            html_content = f"""
            <!DOCTYPE html>
        <html lang="ko">
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
                <title>SainTwo 🤖 : 데이터 분석 자동화 Report Poc</title>
            <style>
                body {{
                    font-family: 'AppleGothic', 'Malgun Gothic', 'Noto Sans KR', sans-serif;
                    line-height: 1.6;
                    margin: 0;
                    padding: 20px;
                    background-color: #f8f9fa;
                    color: #333;
                }}
                .container {{
                    max-width: 1200px;
                    margin: 0 auto;
                    background: white;
                    padding: 30px;
                    border-radius: 10px;
                    box-shadow: 0 0 20px rgba(0,0,0,0.1);
                }}
                .header {{
                    text-align: center;
                    margin-bottom: 40px;
                    padding: 20px;
                    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                    color: white;
                    border-radius: 10px;
                }}
                    .executive-summary-box, .message-effectiveness-box {{
                        background: #f8f9fa;
                        border: 2px solid #e9ecef;
                        border-radius: 12px;
                    padding: 25px;
                        margin: 20px 0;
                        box-shadow: 0 4px 6px rgba(0,0,0,0.1);
                    }}
                    .key-metrics-grid {{
                        display: grid;
                        grid-template-columns: repeat(4, 1fr);
                        gap: 15px;
                        margin: 20px 0;
                    }}
                    .metric-box {{
                        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                        color: white;
                    padding: 20px;
                        border-radius: 8px;
                        text-align: center;
                        box-shadow: 0 4px 6px rgba(0,0,0,0.1);
                    }}
                    .metric-label {{
                        font-size: 0.9em;
                        font-weight: 500;
                        margin-bottom: 8px;
                        opacity: 0.9;
                    }}
                    .metric-value {{
                    font-size: 1.8em;
                        font-weight: bold;
                        margin-bottom: 5px;
                    }}
                    .metric-detail {{
                        font-size: 0.8em;
                        opacity: 0.8;
                    }}
                    .category-grid, .funnel-list {{
                    display: grid;
                        grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
                        gap: 10px;
                        margin: 10px 0;
                    }}
                    .category-item, .funnel-item {{
                        background: white;
                        padding: 15px;
                    border-radius: 8px;
                        border-left: 4px solid #667eea;
                        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
                    }}
                    .funnel-item.high {{
                        border-left-color: #28a745;
                    }}
                    .funnel-item.medium {{
                        border-left-color: #ffc107;
                    }}
                    .funnel-item.low {{
                        border-left-color: #dc3545;
                    }}
                    .message-examples {{
                        display: flex;
                        flex-direction: column;
                        gap: 10px;
                    }}
                    .message-item {{
                        background: white;
                        padding: 15px;
                        border-radius: 8px;
                        display: flex;
                        justify-content: space-between;
                        align-items: center;
                        border-left: 4px solid #6f42c1;
                }}
                .conversion-rate {{
                        background: #28a745;
                        color: white;
                        padding: 5px 10px;
                        border-radius: 15px;
                    font-weight: bold;
                    }}
                    .boxplot-section {{
                        margin: 20px 0;
                        text-align: center;
                    }}
                    .boxplot-chart {{
                    max-width: 100%;
                    height: auto;
                    border-radius: 8px;
                        box-shadow: 0 4px 6px rgba(0,0,0,0.1);
                    }}
                    .keyword-grid {{
                        display: grid;
                        grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
                        gap: 10px;
                        margin: 15px 0;
                    }}
                    .keyword-item {{
                        background: white;
                        padding: 15px;
                    border-radius: 8px;
                    text-align: center;
                        border: 2px solid #e9ecef;
                    }}
                    .keyword {{
                        display: block;
                        font-weight: bold;
                        color: #495057;
                        margin-bottom: 5px;
                    }}
                    .impact {{
                        display: block;
                        color: #28a745;
                        font-weight: bold;
                    }}
                    .tone-features {{
                    display: grid;
                        grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
                        gap: 15px;
                        margin: 15px 0;
                    }}
                    .tone-item {{
                    background: white;
                        padding: 15px;
                    border-radius: 8px;
                        border-left: 4px solid #fd7e14;
                    }}
                    .analysis-table {{
                        width: 100%;
                        border-collapse: collapse;
                        margin: 15px 0;
                        background: white;
                        border-radius: 8px;
                        overflow: hidden;
                        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
                    }}
                    .analysis-table th {{
                        background: #667eea;
                        color: white;
                        padding: 12px;
                        text-align: left;
                        font-weight: 600;
                    }}
                    .analysis-table td {{
                        padding: 12px;
                        border-bottom: 1px solid #e9ecef;
                    }}
                    .analysis-table tr.high {{
                        background-color: #d4edda;
                    }}
                    .analysis-table tr.medium {{
                        background-color: #fff3cd;
                    }}
                    .analysis-table tr.low {{
                        background-color: #f8d7da;
                    }}
                    .grade-badge {{
                        padding: 4px 8px;
                        border-radius: 12px;
                        font-size: 0.8em;
                    font-weight: bold;
                    }}
                    .grade-badge.high {{
                        background: #28a745;
                        color: white;
                    }}
                    .grade-badge.medium {{
                        background: #ffc107;
                        color: #212529;
                    }}
                    .grade-badge.low {{
                        background: #dc3545;
                    color: white;
                }}
                    .insight-section {{
                        margin: 20px 0;
                    }}
                    .pattern-grid {{
                    display: grid;
                        grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
                        gap: 15px;
                        margin: 15px 0;
                    }}
                    .pattern-item {{
                        background: white;
                        padding: 15px;
                        border-radius: 8px;
                        border-left: 4px solid #6f42c1;
                        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
                    }}
                    .conversion-rate {{
                        display: inline-block;
                        background: #28a745;
                        color: white;
                        padding: 4px 8px;
                        border-radius: 12px;
                        font-size: 0.8em;
                        font-weight: bold;
                        margin-top: 8px;
                    }}
                    .funnel-strategy-section {{
                        margin: 25px 0;
                    }}
                    .strategy-groups {{
                        display: flex;
                        flex-direction: column;
                        gap: 20px;
                    }}
                    .strategy-group {{
                        background: white;
                    padding: 20px;
                    border-radius: 8px;
                        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
                }}
                    .strategy-group.high-group {{
                        border-left: 4px solid #28a745;
                }}
                    .strategy-group.medium-group {{
                        border-left: 4px solid #ffc107;
                }}
                    .strategy-group.low-group {{
                        border-left: 4px solid #dc3545;
                    }}
                    .group-funnels {{
                    display: flex;
                        flex-wrap: wrap;
                        gap: 8px;
                        margin: 10px 0;
                    }}
                    .funnel-tag {{
                        padding: 4px 12px;
                        border-radius: 15px;
                        font-size: 0.8em;
                        font-weight: 500;
                    }}
                    .funnel-tag.high {{
                        background: #d4edda;
                        color: #155724;
                    }}
                    .funnel-tag.medium {{
                        background: #fff3cd;
                        color: #856404;
                    }}
                    .funnel-tag.low {{
                        background: #f8d7da;
                        color: #721c24;
                    }}
                    .strategy-recommendation {{
                        background: #f8f9fa;
                        padding: 15px;
                        border-radius: 6px;
                        margin-top: 10px;
                        line-height: 1.6;
                    }}
                    .insights-text-box, .llm-insights-text-box {{
                        background: #f8f9fa;
                        border: 2px solid #e9ecef;
                        border-radius: 8px;
                        padding: 20px;
                        margin: 20px 0;
                        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
                    }}
                    .insights-content, .llm-insights-content {{
                        line-height: 1.8;
                    }}
                    .insights-content ul, .llm-insights-content ul {{
                        margin: 10px 0;
                        padding-left: 20px;
                    }}
                    .insights-content li, .llm-insights-content li {{
                        margin: 8px 0;
                }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                        <h1>SainTwo : 데이터 분석 자동화 Report Poc</h1>
                    <p>생성일: {datetime.now().strftime('%Y년 %m월 %d일 %H:%M')}</p>
                </div>
                
                    <!-- 첫 번째 박스: Matt Agent : 퍼널 별 성과 분석 -->
                    <div class="executive-summary-box">
                        <h2>Matt Agent: 퍼널 별 성과 분석</h2>
                        
                        <div class="key-metrics-grid">
                            <div class="metric-box">
                                <div class="metric-label">현재 주차</div>
                                <div class="metric-value">{week_number}주차</div>
                    </div>
                            <div class="metric-box">
                                <div class="metric-label">실험군 전환</div>
                                <div class="metric-value">{total_conversions:.0f}건</div>
                                <div class="metric-detail">전체 발송: {total_sent:.0f}건</div>
                    </div>
                            <div class="metric-box">
                                <div class="metric-label">실험군 전환율</div>
                                <div class="metric-value">{exp_rate*100:.1f}%</div>
                    </div>
                            <div class="metric-box">
                                <div class="metric-label">평균 Lift</div>
                                <div class="metric-value">+{total_lift*100:.1f}%p</div>
                                <div class="metric-detail">vs 대조군</div>
                    </div>
                </div>
                
                        {funnel_analysis}
                    </div>
                    
                    <!-- 두 번째 박스: 문구 효과성 분석 & 키워드 패턴 -->
                    <div class="message-effectiveness-box">
                        <h2>📈 문구 효과성 분석 & 키워드 패턴</h2>
                        
                        {message_analysis}
                        
                        <div class="llm-insights">
                            <h4>🧠 LLM 기반 문구 분석 인사이트</h4>
                            
                            <div class="llm-insights-text-box">
                                <h5>📋 LLM 분석 종합 결과</h5>
                                <div class="llm-insights-content">
                                    {self._generate_llm_analysis_content()}
                                </div>
                </div>
                
                            {self._generate_keyword_analysis()}
                            {self._generate_pattern_analysis()}
                            {self._generate_tone_effectiveness()}
                        </div>
                </div>
            </div>
        </body>
        </html>
        """
            
            return html_content
            
        except Exception as e:
            return f"<div class='error'>새로운 경영진용 보고서 생성 오류: {str(e)}</div>"
        
    def generate_comprehensive_report(self, agent_results: Dict[str, Any]) -> str:
        """종합 리포트 생성"""
        print("🚀 종합 HTML 리포트 생성 시작...")
        
        # 데이터 로드
        self.load_data()
        
        # Agent 결과 설정
        self.set_agent_results(agent_results)
        
        # HTML 리포트 생성 (2박스 구조)
        html_content = self.generate_new_executive_report()
        
        # 파일 저장 (날짜시간 prefix 추가)
        datetime_prefix = get_datetime_prefix()
        
        # 날짜별 폴더 생성
        from datetime import datetime
        today = datetime.now().strftime('%Y%m%d')
        reports_dir = f"outputs/reports/{today}"
        os.makedirs(reports_dir, exist_ok=True)
        
        report_path = f"{reports_dir}/{datetime_prefix}_comprehensive_data_analysis_report.html"
        with open(report_path, 'w', encoding='utf-8') as f:
            f.write(html_content)
            
        print(f"✅ 종합 HTML 리포트 생성 완료: {report_path}")
        return report_path

def create_comprehensive_html_report(csv_file_path: str, agent_results: Dict[str, Any]) -> str:
    """종합 HTML 리포트 생성 함수"""
    generator = ComprehensiveHTMLReportGenerator(csv_file_path)
    return generator.generate_comprehensive_report(agent_results)

if __name__ == "__main__":
    # 테스트용
    agent_results = {
        'data_understanding': '데이터 이해 분석 결과...',
        'statistical_analysis': '통계 분석 결과...',
        'llm_analysis': 'LLM 분석 결과...',
        'comprehensive_analysis': '종합 분석 결과...'
    }
    
    report_path = create_comprehensive_html_report("clean_df_renamed.csv", agent_results)
    print(f"리포트 생성 완료: {report_path}")

