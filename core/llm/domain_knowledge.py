"""쏘카 도메인 지식 및 용어 검증 모듈"""

import re
from typing import Dict, Any, List

class DomainKnowledge:
    """쏘카 도메인 지식 및 컬럼 설명"""
    
    @staticmethod
    def get_company_context():
        """회사 및 서비스 도메인 설명"""
        return """
        # 쏘카(SOCAR) 서비스 도메인 지식
        
        ## 회사 개요
        - 쏘카는 대한민국의 대표적인 카셰어링 서비스 플랫폼
        - 고객이 원하는 시간에 10분 단위로 차량을 예약하고 주차장에 반납하는 서비스
        - 주차장에서 차량을 빌려서 사용 후, 다시 그 주차장에 반납하는 순환형 서비스
        
        ## 핵심 서비스 용어
        - **쏘카존**: 쏘카 차량이 주차되어 있는 전용 주차장
        - **주행요금 개편**: 차량 대여 및 운전을 통한 비용 제출 요금 변경
        - **배차**: 차량을 해당 주차장(쏘카존)에 배치하는 행위
        - **반차**: 차량을 주차장(쏘카존)에 반납하는 행위
        - **예약**: 고객이 원하는 시간에 차량을 10분 단위로 예약하는 행위
        - **쏘카 패스**: 정기 구독을 통해 대여요금 할인 쿠폰을 제공하는 멤버십
        - **패스포트**: 쏘카·타다 통합 멤버십, 할인과 크레딧 적립 제공
        - **쏘카 페어링**: 장기렌트 차량을 다른 회원과 공유해 대여료를 절감하는 서비스
        - **쏘카 플랜**: 1개월~36개월 기간제 장기 대여 서비스
        - **쏘카 세이브**: 구형 차량 예약 시 추가 할인 제공 서비스
        - **쏘카 클럽**: 누적 주행거리에 따른 회원 등급제 혜택 프로그램
        - **쏘카 부름 서비스**: 원하는 장소로 차량을 배달해주는 유료 서비스
        - **쏘카 핸들/핸들러**: 회원이 차량 운영 미션(세차·탁송 등)에 참여하고 리워드 받는 프로그램
        
        ## 비즈니스 모델
        - 고객은 앱을 통해 차량을 예약하고 쏘카존에서 픽업
        - 사용 후 동일한 쏘카존에 반납
        - 시간 단위(10분)로 과금되는 유연한 서비스
    
        """
    
    @staticmethod
    def get_column_descriptions():
        """컬럼별 상세 설명"""
        return """
        # 쏘카 CRM 데이터 컬럼 상세 설명
        
        ## 기본 정보
        - **실행일**: CRM 문구를 실험군, 대조군에게 문구를 전송한 날짜 (Column type: date)
        
        ## 퍼널 및 타겟팅
        - **퍼널**: 모바일 앱에서 유저가 이탈한 퍼널 단계, 해당 퍼널에서 이탈한 유저 대상으로 CRM 문구를 전송함 (Column type: String)
        - **소재**: CRM 마케터가 문구를 유저에게 전송해 개선하고자 한 목적 (FOMO는 Fear of Missing Out으로서 고객이 조회한 차량을 놓칠 수 있다는 공포 마케팅 방법, 주행요금 개편은 주행 요금 개편 내용을 고객에게 알려 예약 전환을 유도한 것, 이탈은 이탈한 유저에게 전송하여 예약 전환을 유도한 것, 실적 대응은 CRM 마케터가 실적을 올리기 위한 진행한 액션) (Column type: String)
        - **목적**: CRM 마케터가 해당 퍼널 단계에서 해당 문구로 예약 전환율을 높이기 위해 전송한 목적, 목적은 소재를 통해 개선하고자 한 목적을 보다 세부적으로 설명하고 있음 (Column type: String)
        - **타겟**: 퍼널에서 이탈한 고객군 중, 보다 세부적으로 타겟팅을 정밀화한 내용 (예: T4_존 마커 클릭 유저라면, 이용시간 3일 이상 설정 후 제주공항존(5개) 클릭했으나 1시간 내 예약전환 없는 회원) (Column type: String)
        - **이탈 가설**: 퍼널 단계 고객들이 이탈했을 것 같은 이유를 추정한 가설 (Column type: String)
        
        ## 메시지 및 콘텐츠
        - **문구**: 퍼널 단계에서 이탈한 고객에게 CRM 마케팅으로 사용한 문구 (#NAME이라고 된 부분은 고객의 이름이 개인화되어 들어가는 곳) (Column type: String)
        - **랜딩**: 고객이 해당 CRM 마케팅을 통해 앱으로 접속시, 랜딩되는 페이지 정보 (가지러가기는 쏘카존에서 차량을 빌릴 수 있는 페이지, 여기로 부르기는 부름이라는 쏘카 서비스가 있는데 차량을 유저가 원하는 위치에 차량을 부를 수 있는 서비스, 마지막 탐색존은 고객이 앱 사용 중 마지막으로 차량을 탐색했던 존) (Column type: String)
        - **추가 혜택**: CRM 마케팅으로 제공되는 추가 혜택 (Column type: String)
        
        ## 채널 및 플랫폼
        - **채널**: 마케팅 채널 (Column type: String)
        
        ## 고객 세그먼트
        - **서비스 생애 단계**: 고객의 쏘카 서비스 이용 단계 (신규회원, 당일 접속, 3일 내 접속 등, 이탈 회원은 30일이내 접속한 회원) (Column type: String)
        - **타겟 연령**: 타겟 고객의 연령대, NULL 값은 전체 연령 대상으로 진행한 것 (Column type: String)
        - **설정시간**: 쏘카는 차량을 10분 단위로 본인이 원하는 시간만큼 차량을 예약하고 빌리는 시스템임. 설정시간은 CRM 마케팅 전송시 해당 조건에 맞는 유저들만 보낸 것으로 필터를 건 것 (4시간 미만은 4시간 미만 대여로 세팅, 4시간 이상 ~ 10시간 미만은 해당 시간 대여로 세팅, 48시간 이상은 48시간 이상 대여로 세팅) (Column type: String)
        - **리드타임**: 리드타임은 차량 출발 시작 시간과 예약을 생성한 시작 시간 차이를 의미함. CRM 마케팅 전송시 해당 조건에 맞는 유저들만 보낸 것으로 필터를 건 것 (4시간 미만은 4시간 미만 대여로 리드타임이 세팅된 사람, 4시간 이상 ~ 10시간 미만은 해당 시간 대여로 세팅된 사람, 48시간 이상은 48시간 이상 대여로 세팅된 사람) (Column type: String)
        - **출발시각**: 차량이 출발되는 시작 시간을 의미함 (Column type: datetime, however the content is string)
        - **차종**: 차량 종류 (Column type: String)
        
        ## 실험 및 대조군
        - **실험군**: 실험군은 A/B Test 대상에 해당 메세지를 받은 유저들임 (TG_푸시_남성은 남성 푸시 실험군, TG_푸시_여성은 여성 푸시 실험군) (Column type: String)
        - **대조군**: 대조군은 A/B Test 대상에 해당 메세지를 받지 않은 유저들임 (Column type: String)
        
        ## 성과 지표 (실험군)
        - **발송**: 실험군에게 문구를 전송한 건수 (Column type: Integer and counts by variant)
        - **1일이내 예약생성**: 실험군 중 1일 이내 예약 생성 건수 (Column type: float and counts by variant)
        - **예약전환율**: 예약 전환율 (Column type: float and conversion rate by variant)
        - **3일이내 예약생성**: 실험군 중 3일 이내 예약 생성 건수 (Column type: float and counts by variant)
        - **예약전환율.1**: 3일 이내 예약 전환율 (Column type: float and conversion rate by variant)
        - **7일이내 예약생성**: 실험군 중 7일 이내 예약 생성 건수 (Column type: float and counts by variant)
        - **예약전환율.2**: 7일 이내 예약 전환율 (Column type: float and conversion rate by variant)
        
        ## 성과 지표 (대조군)
        - **발송.1**: 대조군 발송 건수, 원래는 대조군이기 때문에 메세지를 수신하지 말아야 하나, 데이터 추출 시 대조군에게 메세지를 전송한 건수를 의미함 (Column type: Integer)
        - **1일이내 예약생성.1**: 대조군 1일 이내 예약 생성 건수 (Column type: float and counts by control)
        - **예약전환율.3**: 대조군 예약 전환율 (Column type: float and conversion rate by control)
        
        ## 전처리 후 컬럼명 (실제 분석에서 사용)
        - **실험군_발송**: 실험군에게 문구를 전송한 건수
        - **실험군_1일이내_예약생성**: 실험군 중 1일 이내 예약 생성 건수
        - **실험군_예약전환율**: 실험군 예약 전환율
        - **실험군_3일이내_예약생성**: 실험군 중 3일 이내 예약 생성 건수
        - **실험군_3일이내_예약전환율**: 실험군 3일 이내 예약 전환율
        - **실험군_7일이내_예약생성**: 실험군 중 7일 이내 예약 생성 건수
        - **실험군_7일이내_예약전환율**: 실험군 7일 이내 예약 전환율
        - **대조군_발송**: 대조군 발송 건수
        - **대조군_1일이내_예약생성**: 대조군 1일 이내 예약 생성 건수
        - **대조군_예약전환율**: 대조군 예약 전환율
        """
    
    @staticmethod
    def get_business_context():
        """비즈니스 컨텍스트 및 분석 목적"""
        return """
        # 비즈니스 분석 컨텍스트
        
        ## 분석 목적
        - CRM 캠페인의 효과성 측정 및 최적화
        - 퍼널별 고객 이탈 방지 전략 수립
        - 문구별 전환율 최적화를 통한 수익성 향상
        - 주차별 트렌드 분석을 통한 캠페인 타이밍 최적화
        
        ## 핵심 성과 지표 (KPI)
        - **전환율**: 발송 대비 예약 생성 비율
        - **퍼널별 성과**: 각 퍼널 단계별 전환율
        - **문구별 효과성**: 메시지별 전환율 차이
        - **채널별 성과**: 전송 채널별 효과성
        - **시간별 트렌드**: 주차별, 일별 성과 변화
        
        ## 분석 관점
        - **고객 여정**: 퍼널 단계별 고객 행동 패턴
        - **메시지 최적화**: 문구별 효과성 분석
        - **채널 최적화**: 전송 채널별 성과 비교
        - **타이밍 최적화**: 주차별, 시간별 최적 전송 시점
        - **세그먼트별 차이**: 고객 그룹별 반응 차이
        """
    
    @staticmethod
    def get_analysis_guidelines():
        """분석 가이드라인 및 주의사항"""
        return """
        # 분석 가이드라인 및 주의사항
        
        ## 데이터 품질 고려사항
        - **결측치**: 많은 컬럼에 결측치가 있으므로 분석 시 주의
        - **데이터 타입**: 숫자형 컬럼에 문자열이 포함될 수 있음
        - **중복 데이터**: 중복 행이 존재하므로 제거 필요
        - **발송량 필터링**: 최소 500건 이상의 발송량을 가진 데이터만 분석
        
        ## 분석 시 고려사항
        - **퍼널 단계**: 고객이 이탈한 퍼널 단계를 정확히 파악
        - **문구 분석**: 한글 텍스트이므로 의미적 분석 필요
        - **시간적 트렌드**: 주차별, 일별 패턴 분석
        - **채널별 차이**: 각 채널의 특성과 고객 반응 차이
        - **세그먼트별 차이**: 고객 그룹별 반응 패턴 차이
        
        ## 비즈니스 인사이트 도출
        - **전환율 향상**: 어떤 퍼널, 문구, 채널이 효과적인지
        - **이탈 방지**: 고객이 이탈하는 퍼널 단계와 원인
        - **최적화 방안**: 캠페인 개선을 위한 구체적 제안
        - **예측 분석**: 향후 성과 예측 및 전략 수립
        """

class DomainTerminology:
    """도메인 용어 사전 및 이해도 검증"""
    
    @staticmethod
    def get_domain_terms():
        """쏘카 도메인 핵심 용어 사전"""
        return {
            # 서비스 핵심 용어
            "쏘카": "카셰어링 서비스 플랫폼",
            "쏘카존": "쏘카 차량이 주차되어 있는 전용 주차장",
            "카셰어링": "차량을 시간 단위로 대여하는 서비스",
            "배차": "차량을 해당 주차장(쏘카존)에 배치하는 행위",
            "반차": "차량을 주차장(쏘카존)에 반납하는 행위",
            "예약": "고객이 원하는 시간에 차량을 10분 단위로 예약하는 행위",
            "개편": "주행요금 개편",
            "주차": "쏘카존에서 대여한 차량을 주차장에 반납하는 행위",
            
            # 비즈니스 용어
            "퍼널": "고객 여정의 단계별 경로 (인지→관심→고려→구매→이용)",
            "이탈": "고객이 특정 퍼널 단계에서 서비스를 떠나는 행위",
            "전환율": "발송 대비 예약 생성 비율 (%)",
            "CRM": "고객 관계 관리 시스템",
            "세그먼트": "고객을 특정 기준으로 나눈 그룹",
            
            #CRM 칼럼 설명
            
            # 기술/플랫폼 용어
            "Braze": "마케팅 자동화 플랫폼",
            "푸시": "모바일 앱 푸시 알림",
            "인앱메시지": "앱 내에서 표시되는 메시지",
            "랜딩페이지": "클릭 시 이동하는 웹페이지",
            
            # 데이터 분석 용어
            "A/B테스트": "두 가지 버전을 비교하는 실험",
            "실험군": "A/B 테스트의 실험 그룹",
            "대조군": "A/B 테스트의 대조 그룹",
            "순증": "순증가 건수",
            "리드타임": "캠페인 실행 전 준비 시간",
            
            # 고객 세그먼트 용어
            "액티브회원": "활발히 서비스를 이용하는 회원",
            "미접속인": "일정 기간 앱에 접속하지 않은 회원",
            "패스포트": "쏘카의 구독 서비스",
            "법인카드": "법인용 결제 카드",
            "크레딧": "쏘카 내 가상 화폐",
        }
    
    @staticmethod
    def get_technical_terms():
        """기술적/분석 용어 사전"""
        return {
            "벡터유사도": "텍스트 간 의미적 유사성을 수치로 측정하는 방법",
            "시계열분석": "시간에 따른 데이터 변화 패턴을 분석하는 방법",
            "상관관계": "두 변수 간의 연관성을 측정하는 통계적 개념",
            "유의성검정": "통계적 결과가 우연이 아닌지 검증하는 방법",
            "세그먼트분석": "고객 그룹별 차이를 분석하는 방법",
            "트렌드분석": "시간에 따른 변화 패턴을 파악하는 분석",
            "전환율최적화": "전환율을 높이기 위한 개선 작업",
            "이탈방지": "고객 이탈을 막기 위한 전략",
        }
    
    @staticmethod
    def get_business_metrics():
        """비즈니스 지표 용어 사전"""
        return {
            "KPI": "핵심 성과 지표 (Key Performance Indicator)",
            "ROI": "투자 대비 수익률 (Return on Investment)",
            "LTV": "고객 생애 가치 (Lifetime Value)",
            "CAC": "고객 획득 비용 (Customer Acquisition Cost)",
            "ARPU": "고객당 평균 수익 (Average Revenue Per User)",
            "MAU": "월간 활성 사용자 (Monthly Active Users)",
            "DAU": "일간 활성 사용자 (Daily Active Users)",
            "리텐션": "고객 유지율",
            "첨부율": "고객 이탈율",
        }
    
    @staticmethod
    def get_all_terms():
        """모든 도메인 용어 통합"""
        return {
            **DomainTerminology.get_domain_terms(),
            **DomainTerminology.get_technical_terms(),
            **DomainTerminology.get_business_metrics()
        }

class TerminologyValidator:
    """용어 이해도 검증 및 미이해 용어 식별"""
    
    def __init__(self):
        self.domain_terms = DomainTerminology.get_all_terms()
        self.unknown_terms = set()
        self.term_confidence = {}
    
    def extract_terms_from_text(self, text: str) -> List[str]:
        """텍스트에서 도메인 용어 추출"""
        # 한글 용어 추출 (2글자 이상)
        korean_terms = re.findall(r'[가-힣]{2,}', text)
        
        # 영문 용어 추출 (대문자 포함)
        english_terms = re.findall(r'[A-Z][a-zA-Z]*', text)
        
        # 숫자+한글 조합 (예: 30일내, 1일이내)
        number_korean = re.findall(r'\d+[가-힣]+', text)
        
        # 특수 패턴 (예: A/B테스트, 퍼널.1)
        special_patterns = re.findall(r'[A-Z]/[A-Z][가-힣]*', text)
        
        all_terms = korean_terms + english_terms + number_korean + special_patterns
        return list(set(all_terms))  # 중복 제거
    
    def validate_terms(self, text: str) -> Dict[str, Any]:
        """용어 이해도 검증 및 미이해 용어 식별"""
        extracted_terms = self.extract_terms_from_text(text)
        
        known_terms = []
        unknown_terms = []
        ambiguous_terms = []
        
        for term in extracted_terms:
            if term in self.domain_terms:
                known_terms.append({
                    "term": term,
                    "definition": self.domain_terms[term],
                    "confidence": "high"
                })
            elif any(term in key for key in self.domain_terms.keys()):
                # 부분 일치하는 용어
                ambiguous_terms.append({
                    "term": term,
                    "suggestions": [key for key in self.domain_terms.keys() if term in key],
                    "confidence": "medium"
                })
            else:
                # 알 수 없는 용어
                unknown_terms.append({
                    "term": term,
                    "confidence": "low",
                    "context": self._get_term_context(text, term)
                })
        
        return {
            "total_terms": len(extracted_terms),
            "known_terms": known_terms,
            "unknown_terms": unknown_terms,
            "ambiguous_terms": ambiguous_terms,
            "understanding_score": len(known_terms) / len(extracted_terms) if extracted_terms else 1.0
        }
    
    def _get_term_context(self, text: str, term: str) -> str:
        """용어 주변 컨텍스트 추출"""
        # 용어 주변 50자씩 추출
        pattern = f".{{0,50}}{re.escape(term)}.{{0,50}}"
        match = re.search(pattern, text)
        
        if match:
            return match.group(0)
        return ""
    
    def get_terminology_report(self, text: str) -> Dict[str, Any]:
        """용어 이해도 종합 보고서"""
        validation_result = self.validate_terms(text)
        
        return {
            "terminology_analysis": validation_result,
            "recommendations": self._generate_recommendations(validation_result),
            "domain_knowledge_gaps": self._identify_knowledge_gaps(validation_result),
            "suggested_terms": self._suggest_terms_to_learn(validation_result)
        }
    
    def _generate_recommendations(self, validation_result: Dict) -> List[str]:
        """용어 이해도 기반 추천사항"""
        recommendations = []
        
        if validation_result["understanding_score"] < 0.7:
            recommendations.append("도메인 용어 이해도가 낮습니다. 쏘카 서비스 용어를 학습하세요.")
        
        if validation_result["unknown_terms"]:
            recommendations.append(f"{len(validation_result['unknown_terms'])}개의 미이해 용어가 있습니다.")
        
        if validation_result["ambiguous_terms"]:
            recommendations.append("모호한 용어들이 있습니다. 정확한 용어를 확인하세요.")
        
        return recommendations
    
    def _identify_knowledge_gaps(self, validation_result: Dict) -> List[str]:
        """지식 격차 식별"""
        gaps = []
        
        for unknown_term in validation_result["unknown_terms"]:
            gaps.append(f"'{unknown_term['term']}': {unknown_term['context']}")
        
        return gaps
    
    def _suggest_terms_to_learn(self, validation_result: Dict) -> List[str]:
        """학습 권장 용어 제안"""
        suggestions = []
        
        # 미이해 용어들
        for unknown_term in validation_result["unknown_terms"]:
            suggestions.append(unknown_term["term"])
        
        # 모호한 용어들
        for ambiguous_term in validation_result["ambiguous_terms"]:
            suggestions.extend(ambiguous_term["suggestions"])
        
        return list(set(suggestions))
