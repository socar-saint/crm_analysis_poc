"""간단한 LLM 기반 용어 검증 도구"""

import re
import json
import pandas as pd
from typing import Dict, Any, List
from core.llm.domain_knowledge import DomainKnowledge
import litellm
from config.settings import settings

# Azure OpenAI 모델 설정
azure_llm = litellm

def validate_csv_terms_with_llm(csv_file_path: str) -> Dict[str, Any]:
    """CSV 파일의 용어들을 LLM으로 검증"""
    print("--- Tool: validate_csv_terms_with_llm called ---")
    
    try:
        # 1. CSV에서 용어 추출
        df = pd.read_csv(csv_file_path)
        all_text = ""
        for col in df.columns:
            if df[col].dtype == 'object':
                all_text += " " + df[col].astype(str).str.cat(sep=" ")
        
        # 한글 용어 추출 (2글자 이상)
        korean_terms = re.findall(r'[가-힣]{2,}', all_text)
        english_terms = re.findall(r'[A-Z][a-zA-Z]*', all_text)
        all_terms = list(set(korean_terms + english_terms))
        
        # 2. 도메인 용어사전 로드
        from core.llm.domain_knowledge import DomainTerminology
        domain_terms = DomainTerminology.get_domain_terms()
        technical_terms = DomainTerminology.get_technical_terms()
        business_metrics = DomainTerminology.get_business_metrics()
        all_domain_terms = {**domain_terms, **technical_terms, **business_metrics}
        
        # 3. 배치로 용어 이해도 평가 (API 호출 최적화)
        term_evaluations = []
        total_score = 0
        
        # 용어 빈도 계산하여 10번 이상 사용된 용어만 분석
        from collections import Counter
        korean_counter = Counter(korean_terms)
        english_counter = Counter(english_terms)
        
        # 10번 이상 사용된 용어 필터링
        korean_frequent = [term for term, count in korean_counter.items() if count >= 10]
        english_frequent = [term for term, count in english_counter.items() if count >= 10]
        frequent_terms = korean_frequent + english_frequent
        
        # 상위 40개 용어를 한 번에 분석 (10번 이상 사용된 용어 중에서)
        terms_to_analyze = frequent_terms[:40] if len(frequent_terms) >= 40 else frequent_terms
        print(f"🚀 배치 용어 분석 중: {len(terms_to_analyze)}개 용어 (10회 이상 사용된 용어 중 상위 {len(terms_to_analyze)}개, API 호출 1회)")
        print(f"📊 10회 이상 사용된 용어 총 개수: {len(frequent_terms)}개 (한글: {len(korean_frequent)}개, 영문: {len(english_frequent)}개)")
        
        # 용어별 컨텍스트와 용어사전 정의 수집
        term_data = []
        for term in terms_to_analyze:
            context = ""
            for col in df.columns:
                if df[col].dtype == 'object':
                    mask = df[col].astype(str).str.contains(term, na=False)
                    if mask.any():
                        context = df[mask][col].astype(str).iloc[0][:100]
                        break
            
            dictionary_definition = all_domain_terms.get(term, None)
            term_data.append({
                "term": term,
                "context": context,
                "dictionary_definition": dictionary_definition
            })
        
        # 배치 프롬프트 생성
        batch_prompt = f"""
        다음 쏘카 CRM 마케팅 데이터의 용어들을 한 번에 분석해주세요:
        
        분석할 용어들:
        {json.dumps(term_data, ensure_ascii=False, indent=2)}
        
        도메인 용어사전:
        {json.dumps(all_domain_terms, ensure_ascii=False, indent=2)}
        
        각 용어에 대해 다음을 평가해주세요:
        1. 용어 이해도 점수 (0-100)
        2. 용어사전 정의와의 일치 여부 (있는 경우)
        3. 도메인 관련성 (없는 경우)
        4. 간단한 설명
        
        다음 JSON 형식으로 답변해주세요:
        {{
            "term_evaluations": [
                {{
                    "term": "용어1",
                    "score": 85,
                    "matches_dictionary": true,
                    "explanation": "용어 설명"
                }},
                {{
                    "term": "용어2",
                    "score": 70,
                    "is_domain_related": true,
                    "explanation": "용어 설명"
                }}
            ],
            "overall_score": 77.5
        }}
        """
        
        try:
            response = azure_llm.completion(
                model=f"azure/{settings.AZURE_OPENAI_DEPLOYMENT_NAME}",
                messages=[{"role": "user", "content": batch_prompt}],
                api_key=settings.AZURE_OPENAI_API_KEY,
                api_base=settings.AZURE_OPENAI_ENDPOINT,
                api_version=settings.AZURE_OPENAI_API_VERSION,
                temperature=0.1
            )
            
            response_text = response.choices[0].message.content
            json_start = response_text.find('{')
            json_end = response_text.rfind('}') + 1
            
            if json_start != -1 and json_end != -1:
                json_str = response_text[json_start:json_end]
                batch_result = json.loads(json_str)
                
                term_evaluations = batch_result.get('term_evaluations', [])
                overall_score = batch_result.get('overall_score', 0)
                total_score = overall_score * len(term_evaluations)
                
                print(f"✅ 배치 분석 완료: 평균 이해도 {overall_score:.1f}%")
            else:
                # JSON 파싱 실패시 기본값
                overall_score = 50
                for term in terms_to_analyze:
                    term_evaluations.append({
                        "term": term,
                        "score": 50,
                        "explanation": "배치 분석 실패"
                    })
                    total_score += 50
                    
        except Exception as e:
            print(f"❌ 배치 분석 중 오류: {str(e)}")
            overall_score = 0
            for term in terms_to_analyze:
                term_evaluations.append({
                    "term": term,
                    "score": 0,
                    "explanation": f"오류: {str(e)}"
                })
        # 4. 결과 정리
        high_terms = [e for e in term_evaluations if e.get("score", 0) >= 70]
        low_terms = [e for e in term_evaluations if e.get("score", 0) < 50]
        
        return {
            "status": "success",
            "csv_file": csv_file_path,
            "total_terms_found": len(all_terms),
            "frequent_terms_count": len(frequent_terms),
            "analyzed_terms": len(terms_to_analyze),
            "overall_score": overall_score,
            "term_evaluations": term_evaluations,
            "high_understanding_terms": high_terms,
            "low_understanding_terms": low_terms,
            "analysis_type": "batch_llm_analysis",
            "message": f"배치 분석 완료: 평균 이해도 {overall_score:.1f}%",
            "summary": {
                "korean_frequent_terms": len(korean_frequent),
                "english_frequent_terms": len(english_frequent),
                "total_frequent_terms": len(frequent_terms),
                "analyzed_terms_count": len(terms_to_analyze),
                "understanding_score": overall_score,
                "low_understanding_terms": len([t for t in term_evaluations if t.get('score', 0) < 70])
            }
        }
        
    except Exception as e:
        return {
            "status": "error",
            "error_message": f"CSV 용어 검증 중 오류: {str(e)}"
        }

def get_domain_glossary() -> Dict[str, Any]:
    """도메인 용어 사전 조회"""
    print("--- Tool: get_domain_glossary called ---")
    
    try:
        from core.llm.domain_knowledge import DomainTerminology
        domain_terms = DomainTerminology.get_domain_terms()
        technical_terms = DomainTerminology.get_technical_terms()
        business_metrics = DomainTerminology.get_business_metrics()
        
        return {
            "status": "success",
            "domain_terms": domain_terms,
            "technical_terms": technical_terms,
            "business_metrics": business_metrics,
            "total_terms": len(domain_terms) + len(technical_terms) + len(business_metrics),
            "message": "도메인 용어 사전을 조회했습니다."
        }
        
    except Exception as e:
        return {
            "status": "error",
            "error_message": f"용어 사전 조회 중 오류: {str(e)}"
        }

def validate_csv_terms_simple(csv_file_path: str) -> Dict[str, Any]:
    """간단한 용어 검증 (LLM 호출 없음)"""
    print("--- Tool: validate_csv_terms_simple called ---")
    
    try:
        # 1. CSV에서 용어 추출
        df = pd.read_csv(csv_file_path)
        all_text = ""
        for col in df.columns:
            if df[col].dtype == 'object':
                all_text += " " + df[col].astype(str).str.cat(sep=" ")
        
        # 한글 용어 추출 (2글자 이상)
        korean_terms = re.findall(r'[가-힣]{2,}', all_text)
        english_terms = re.findall(r'[A-Z][a-zA-Z]*', all_text)
        all_terms = list(set(korean_terms + english_terms))
        
        # 2. 도메인 용어사전 로드
        from core.llm.domain_knowledge import DomainTerminology
        domain_terms = DomainTerminology.get_domain_terms()
        technical_terms = DomainTerminology.get_technical_terms()
        business_metrics = DomainTerminology.get_business_metrics()
        all_domain_terms = {**domain_terms, **technical_terms, **business_metrics}
        
        # 3. 간단한 매칭 분석 (LLM 호출 없음)
        matched_terms = []
        unmatched_terms = []
        
        for term in all_terms[:20]:  # 상위 20개만 분석
            if term in all_domain_terms:
                matched_terms.append({
                    "term": term,
                    "definition": all_domain_terms[term],
                    "category": "domain" if term in domain_terms else "technical" if term in technical_terms else "business"
                })
            else:
                unmatched_terms.append(term)
        
        coverage_rate = len(matched_terms) / len(all_terms[:20]) * 100 if all_terms else 0
        
        return {
            "status": "success",
            "csv_file": csv_file_path,
            "total_terms_found": len(all_terms),
            "analyzed_terms": len(all_terms[:20]),
            "matched_terms": matched_terms,
            "unmatched_terms": unmatched_terms[:10],  # 상위 10개만
            "coverage_rate": coverage_rate,
            "analysis_type": "simple_matching"
        }
        
    except Exception as e:
        return {
            "status": "error",
            "error_message": f"간단한 용어 검증 중 오류: {str(e)}"
        }
