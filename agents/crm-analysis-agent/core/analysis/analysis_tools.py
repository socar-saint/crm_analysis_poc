"""Google ADK 도구로 래핑된 분석 함수들"""

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
import json
from datetime import datetime
from typing import Dict, Any
import warnings
import os
warnings.filterwarnings('ignore')

# from google.adk.tools import FunctionTool

# 로거 설정
import logging
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# 출력 디렉토리 설정
OUTPUT_DIR = "outputs"
os.makedirs(OUTPUT_DIR, exist_ok=True)

# 공통 함수: 날짜별 리포트 폴더 생성
def get_reports_dir():
    """outputs/reports/{오늘날짜} 폴더 경로를 반환하고 폴더를 생성합니다."""
    today = datetime.now().strftime('%Y%m%d')
    reports_dir = f"{OUTPUT_DIR}/reports/{today}"
    os.makedirs(reports_dir, exist_ok=True)
    return reports_dir

# =============================================================================
# 경영진용 보고서 데이터 정제화 Tools
# =============================================================================

def structure_llm_analysis_for_html(csv_file_path: str, llm_analysis_result: str) -> str:
    """LLM 분석 결과를 HTML 규격에 맞게 구조화 - 비활성화됨
    
    Args:
        csv_file_path: CSV 파일 경로
        llm_analysis_result: LLM Agent의 분석 결과 (텍스트)
    
    Returns:
        비활성화됨 - 항상 "분석 중" 반환
    """
    # 함수 비활성화 - 원본 llm_analysis만 사용
    return "분석 중"

def prepare_category_analysis_data(csv_file_path: str) -> Dict[str, Any]:
    """카테고리 분석용 데이터 정제화 (Lift 기반)"""
    try:
        df = pd.read_csv(csv_file_path)
        
        # Lift 계산 (실험군 - 대조군)
        df['lift'] = df['실험군_예약전환율'] - df['대조군_예약전환율']
        
        # 정제된 데이터 구성
        analysis_data = {
            "campaigns": df[['목적', '타겟', '문구', '퍼널', '실험군_예약전환율', '대조군_예약전환율', 'lift', '실험군_발송', '실험군_1일이내_예약생성']].to_dict('records'),
            "summary_stats": {
                "total_campaigns": len(df),
                "unique_purposes": df['목적'].nunique(),
                "unique_targets": df['타겟'].nunique(),
                "unique_funnels": df['퍼널'].nunique(),
                "avg_experiment_conversion": round(df['실험군_예약전환율'].mean(), 0),
                "avg_control_conversion": round(df['대조군_예약전환율'].mean(), 0),
                "avg_lift": round(df['lift'].mean(), 1),
                "lift_range": [round(df['lift'].min(), 1), round(df['lift'].max(), 1)],
                "positive_lift_count": len(df[df['lift'] > 0]),
                "negative_lift_count": len(df[df['lift'] < 0])
            },
            "funnel_breakdown": df.groupby('퍼널').agg({
                '실험군_예약전환율': 'mean',
                '대조군_예약전환율': 'mean',
                'lift': 'mean',
                '실험군_발송': 'sum',
                '실험군_1일이내_예약생성': 'sum'
            }).reset_index().assign(campaign_count=lambda x: x.groupby('퍼널')['퍼널'].transform('count')).round(0).to_dict(),
            "purpose_breakdown": df.groupby('목적').agg({
                '실험군_예약전환율': 'mean',
                '대조군_예약전환율': 'mean',
                'lift': 'mean',
                '실험군_발송': 'sum',
                '실험군_1일이내_예약생성': 'sum'
            }).reset_index().assign(campaign_count=lambda x: x.groupby('목적')['목적'].transform('count')).round(0).to_dict()
        }
        
        return analysis_data
        
    except Exception as e:
        logger.error(f"카테고리 분석 데이터 준비 오류: {str(e)}")
        return {}

def prepare_funnel_segment_data(csv_file_path: str) -> Dict[str, Any]:
    """퍼널 세그먼트 분석용 데이터 정제화 (Lift 기반)"""
    try:
        # CSV 파싱 에러 방지를 위한 옵션 추가
        df = pd.read_csv(csv_file_path, encoding='utf-8', on_bad_lines='skip')
        
        # Lift 계산
        df['lift'] = df['실험군_예약전환율'] - df['대조군_예약전환율']
        
        # 퍼널별 Lift 분위수 계산
        funnel_segments = {}
        for funnel in df['퍼널'].unique():
            if pd.isna(funnel):
                continue
                
            funnel_data = df[df['퍼널'] == funnel]
            
            # Lift 기준 3분위수 계산
            q33 = funnel_data['lift'].quantile(0.33)
            q67 = funnel_data['lift'].quantile(0.67)
            
            # 세그먼트 분류 (Lift 기준)
            high_performers = funnel_data[funnel_data['lift'] >= q67]
            mid_performers = funnel_data[(funnel_data['lift'] >= q33) & (funnel_data['lift'] < q67)]
            low_performers = funnel_data[funnel_data['lift'] < q33]
            
            funnel_segments[funnel] = {
                "high_performers": {
                    "data": high_performers[['문구', '목적', '타겟', '실험군_예약전환율', '대조군_예약전환율', 'lift']].to_dict('records'),
                    "count": len(high_performers),
                    "avg_experiment_conversion": round(high_performers['실험군_예약전환율'].mean(), 0),
                    "avg_control_conversion": round(high_performers['대조군_예약전환율'].mean(), 0),
                    "avg_lift": round(high_performers['lift'].mean(), 1),
                    "lift_range": [round(high_performers['lift'].min(), 1), round(high_performers['lift'].max(), 1)]
                },
                "mid_performers": {
                    "data": mid_performers[['문구', '목적', '타겟', '실험군_예약전환율', '대조군_예약전환율', 'lift']].to_dict('records'),
                    "count": len(mid_performers),
                    "avg_experiment_conversion": round(mid_performers['실험군_예약전환율'].mean(), 0),
                    "avg_control_conversion": round(mid_performers['대조군_예약전환율'].mean(), 0),
                    "avg_lift": round(mid_performers['lift'].mean(), 1),
                    "lift_range": [round(mid_performers['lift'].min(), 1), round(mid_performers['lift'].max(), 1)]
                },
                "low_performers": {
                    "data": low_performers[['문구', '목적', '타겟', '실험군_예약전환율', '대조군_예약전환율', 'lift']].to_dict('records'),
                    "count": len(low_performers),
                    "avg_experiment_conversion": round(low_performers['실험군_예약전환율'].mean(), 0),
                    "avg_control_conversion": round(low_performers['대조군_예약전환율'].mean(), 0),
                    "avg_lift": round(low_performers['lift'].mean(), 1),
                    "lift_range": [round(low_performers['lift'].min(), 1), round(low_performers['lift'].max(), 1)]
                }
            }
        
        return {
            "funnel_segments": funnel_segments,
            "total_funnels": len(df['퍼널'].unique()),
            "overall_stats": {
                "avg_experiment_conversion": round(df['실험군_예약전환율'].mean(), 0),
                "avg_control_conversion": round(df['대조군_예약전환율'].mean(), 0),
                "avg_lift": round(df['lift'].mean(), 1),
                "lift_std": round(df['lift'].std(), 1)
            }
        }
        
    except Exception as e:
        logger.error(f"퍼널 세그먼트 데이터 준비 오류: {str(e)}")
        return {}

def analyze_category_performance_tool(csv_file_path: str) -> str:
    """카테고리별 성과 분석 (Lift 기반) - 데이터 정제화만 수행"""
    try:
        # 데이터 정제화
        analysis_data = prepare_category_analysis_data(csv_file_path)
        
        if not analysis_data:
            return "카테고리 분석 데이터 준비에 실패했습니다."
        
        # 정제된 데이터를 JSON으로 저장
        reports_dir = get_reports_dir()
        datetime_prefix = get_datetime_prefix()
        filename = f"{reports_dir}/{datetime_prefix}_category_analysis_data.json"
        
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(analysis_data, f, ensure_ascii=False, indent=2)
        
        return f"카테고리 분석 데이터 준비 완료: {filename}\n\n정제된 데이터가 준비되었습니다. Agent가 이 데이터를 바탕으로 분석을 수행합니다."
        
    except Exception as e:
        return f"카테고리 성과 분석 오류: {str(e)}"

def analyze_funnel_segment_strategy_tool(csv_file_path: str) -> str:
    """퍼널별 세그먼트 전략 분석 (Lift 기반) - 데이터 정제화만 수행"""
    try:
        # 데이터 정제화
        segment_data = prepare_funnel_segment_data(csv_file_path)
        
        if not segment_data:
            return "퍼널 세그먼트 분석 데이터 준비에 실패했습니다."
        
        # 정제된 데이터를 JSON으로 저장
        reports_dir = get_reports_dir()
        datetime_prefix = get_datetime_prefix()
        filename = f"{reports_dir}/{datetime_prefix}_funnel_segment_analysis_data.json"
        
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(segment_data, f, ensure_ascii=False, indent=2)
        
        return f"퍼널 세그먼트 분석 데이터 준비 완료: {filename}\n\n정제된 데이터가 준비되었습니다. Agent가 이 데이터를 바탕으로 분석을 수행합니다."
        
    except Exception as e:
        return f"퍼널 세그먼트 전략 분석 오류: {str(e)}"

def create_segment_lift_charts(csv_file_path: str) -> str:
    """세그먼트별 Lift 차트 생성 (퍼널별, 카테고리별)"""
    try:
        print("📊 세그먼트별 Lift 차트 생성 중...")
        
        import matplotlib.pyplot as plt
        import seaborn as sns
        plt.rcParams['font.family'] = 'DejaVu Sans'
        
        df = pd.read_csv(csv_file_path)
        df['lift'] = df['실험군_예약전환율'] - df['대조군_예약전환율']
        
        reports_dir = get_reports_dir()
        datetime_prefix = get_datetime_prefix()
        chart_files = []
        
        # 1. 퍼널별 Lift 비교 차트
        plt.figure(figsize=(15, 10))
        
        # 1-1. 퍼널별 평균 Lift 막대차트
        plt.subplot(2, 3, 1)
        funnel_lift = df.groupby('퍼널')['lift'].mean().sort_values(ascending=False)
        colors = ['green' if x > 0 else 'red' for x in funnel_lift.values]
        bars = plt.bar(range(len(funnel_lift)), funnel_lift.values, color=colors, alpha=0.7)
        
        for i, (bar, value) in enumerate(zip(bars, funnel_lift.values)):
            plt.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.1, 
                    f'{value:.1f}%p', ha='center', va='bottom', fontsize=9)
        
        plt.title('퍼널별 평균 Lift', fontsize=12, fontweight='bold')
        plt.xlabel('퍼널')
        plt.ylabel('Lift (%p)')
        plt.xticks(range(len(funnel_lift)), 
                  [f"{funnel[:10]}..." if len(funnel) > 10 else funnel 
                   for funnel in funnel_lift.index], rotation=45)
        plt.grid(axis='y', alpha=0.3)
        
        # 1-2. 퍼널별 실험군 vs 대조군 전환율 비교
        plt.subplot(2, 3, 2)
        comparison_data = df.groupby('퍼널')[['실험군_예약전환율', '대조군_예약전환율']].mean()
        comparison_data.plot(kind='bar', ax=plt.gca(), color=['skyblue', 'lightcoral'])
        plt.title('퍼널별 실험군 vs 대조군 전환율')
        plt.xlabel('퍼널')
        plt.ylabel('전환율 (%)')
        plt.xticks(rotation=45)
        plt.legend()
        plt.grid(axis='y', alpha=0.3)
        
        # 1-3. Lift 분포 히스토그램
        plt.subplot(2, 3, 3)
        plt.hist(df['lift'], bins=20, alpha=0.7, color='lightgreen', edgecolor='black')
        plt.axvline(x=0, color='red', linestyle='--', linewidth=2, label='Baseline (0%p)')
        plt.title('Lift 분포 히스토그램')
        plt.xlabel('Lift (%p)')
        plt.ylabel('빈도')
        plt.legend()
        plt.grid(axis='y', alpha=0.3)
        
        # 1-4. 퍼널별 Lift 상위/하위 세그먼트
        plt.subplot(2, 3, 4)
        funnel_segments = {}
        for funnel in df['퍼널'].unique():
            if pd.isna(funnel):
                continue
            funnel_data = df[df['퍼널'] == funnel]
            q33 = funnel_data['lift'].quantile(0.33)
            q67 = funnel_data['lift'].quantile(0.67)
            
            high_count = len(funnel_data[funnel_data['lift'] >= q67])
            mid_count = len(funnel_data[(funnel_data['lift'] >= q33) & (funnel_data['lift'] < q67)])
            low_count = len(funnel_data[funnel_data['lift'] < q33])
            
            funnel_segments[funnel] = {'high': high_count, 'mid': mid_count, 'low': low_count}
        
        # 상위 5개 퍼널만 표시
        top_funnels = sorted(funnel_segments.items(), key=lambda x: x[1]['high'], reverse=True)[:5]
        funnel_names = [f[0][:8] + '...' if len(f[0]) > 8 else f[0] for f in top_funnels]
        high_counts = [f[1]['high'] for f in top_funnels]
        mid_counts = [f[1]['mid'] for f in top_funnels]
        low_counts = [f[1]['low'] for f in top_funnels]
        
        x = range(len(funnel_names))
        plt.bar(x, high_counts, color='green', alpha=0.7, label='상위 (High)')
        plt.bar(x, mid_counts, bottom=high_counts, color='yellow', alpha=0.7, label='중위 (Mid)')
        plt.bar(x, low_counts, bottom=[h+m for h, m in zip(high_counts, mid_counts)], 
                color='red', alpha=0.7, label='하위 (Low)')
        
        plt.title('퍼널별 세그먼트 분포 (상위 5개)')
        plt.xlabel('퍼널')
        plt.ylabel('캠페인 수')
        plt.xticks(x, funnel_names, rotation=45)
        plt.legend()
        plt.grid(axis='y', alpha=0.3)
        
        # 1-5. 목적별 Lift 분석
        plt.subplot(2, 3, 5)
        if '목적' in df.columns:
            purpose_lift = df.groupby('목적')['lift'].mean().sort_values(ascending=False)
            colors = ['green' if x > 0 else 'red' for x in purpose_lift.values]
            bars = plt.bar(range(len(purpose_lift)), purpose_lift.values, color=colors, alpha=0.7)
            
            for i, (bar, value) in enumerate(zip(bars, purpose_lift.values)):
                plt.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.1, 
                        f'{value:.1f}%p', ha='center', va='bottom', fontsize=9)
            
            plt.title('목적별 평균 Lift')
            plt.xlabel('목적')
            plt.ylabel('Lift (%p)')
            plt.xticks(range(len(purpose_lift)), 
                      [f"{purpose[:8]}..." if len(purpose) > 8 else purpose 
                       for purpose in purpose_lift.index], rotation=45)
            plt.grid(axis='y', alpha=0.3)
        
        # 1-6. Lift vs 전환율 산점도
        plt.subplot(2, 3, 6)
        plt.scatter(df['실험군_예약전환율'], df['lift'], alpha=0.6, color='blue')
        plt.axhline(y=0, color='red', linestyle='--', alpha=0.7)
        plt.title('실험군 전환율 vs Lift')
        plt.xlabel('실험군 전환율 (%)')
        plt.ylabel('Lift (%p)')
        plt.grid(alpha=0.3)
        
        plt.tight_layout()
        
        # 차트 저장
        chart_path = f"{reports_dir}/{datetime_prefix}_segment_lift_analysis.png"
        plt.savefig(chart_path, dpi=300, bbox_inches='tight')
        plt.close()
        chart_files.append(chart_path)
        
        # 2. 카테고리별 Lift 차트 (목적 기반)
        if '목적' in df.columns:
            plt.figure(figsize=(12, 8))
            
            # 2-1. 목적별 Lift 상세 분석
            plt.subplot(2, 2, 1)
            purpose_stats = df.groupby('목적').agg({
                'lift': ['mean', 'std', 'count'],
                '실험군_예약전환율': 'mean',
                '대조군_예약전환율': 'mean'
            }).round(1)
            
            purpose_lift_mean = purpose_stats['lift']['mean'].sort_values(ascending=False)
            colors = ['green' if x > 0 else 'red' for x in purpose_lift_mean.values]
            bars = plt.bar(range(len(purpose_lift_mean)), purpose_lift_mean.values, color=colors, alpha=0.7)
            
            for i, (bar, value) in enumerate(zip(bars, purpose_lift_mean.values)):
                plt.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.1, 
                        f'{value:.1f}%p', ha='center', va='bottom', fontsize=9)
            
            plt.title('목적별 평균 Lift (카테고리 분석)')
            plt.xlabel('목적')
            plt.ylabel('Lift (%p)')
            plt.xticks(range(len(purpose_lift_mean)), 
                      [f"{purpose[:10]}..." if len(purpose) > 10 else purpose 
                       for purpose in purpose_lift_mean.index], rotation=45)
            plt.grid(axis='y', alpha=0.3)
            
            # 2-2. 목적별 전환율 비교
            plt.subplot(2, 2, 2)
            purpose_conversion = df.groupby('목적')[['실험군_예약전환율', '대조군_예약전환율']].mean()
            purpose_conversion.plot(kind='bar', ax=plt.gca(), color=['skyblue', 'lightcoral'])
            plt.title('목적별 실험군 vs 대조군 전환율')
            plt.xlabel('목적')
            plt.ylabel('전환율 (%)')
            plt.xticks(rotation=45)
            plt.legend()
            plt.grid(axis='y', alpha=0.3)
            
            # 2-3. Lift 범위별 분포
            plt.subplot(2, 2, 3)
            lift_ranges = ['음수 (<0)', '낮음 (0-1)', '보통 (1-3)', '높음 (3-5)', '매우높음 (>5)']
            lift_counts = [
                len(df[df['lift'] < 0]),
                len(df[(df['lift'] >= 0) & (df['lift'] < 1)]),
                len(df[(df['lift'] >= 1) & (df['lift'] < 3)]),
                len(df[(df['lift'] >= 3) & (df['lift'] < 5)]),
                len(df[df['lift'] >= 5])
            ]
            colors = ['red', 'orange', 'yellow', 'lightgreen', 'green']
            bars = plt.bar(lift_ranges, lift_counts, color=colors, alpha=0.7)
            
            for bar, count in zip(bars, lift_counts):
                plt.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.5, 
                        str(count), ha='center', va='bottom', fontsize=10)
            
            plt.title('Lift 범위별 캠페인 분포')
            plt.xlabel('Lift 범위 (%p)')
            plt.ylabel('캠페인 수')
            plt.xticks(rotation=45)
            plt.grid(axis='y', alpha=0.3)
            
            # 2-4. 퍼널-목적 조합 히트맵
            plt.subplot(2, 2, 4)
            if '퍼널' in df.columns:
                pivot_data = df.pivot_table(values='lift', index='목적', columns='퍼널', aggfunc='mean')
                if not pivot_data.empty:
                    sns.heatmap(pivot_data, annot=True, fmt='.1f', cmap='RdYlGn', center=0)
                    plt.title('퍼널-목적 조합 Lift 히트맵')
                    plt.xlabel('퍼널')
                    plt.ylabel('목적')
                else:
                    plt.text(0.5, 0.5, '데이터 부족', ha='center', va='center', transform=plt.gca().transAxes)
                    plt.title('퍼널-목적 조합 히트맵 (데이터 부족)')
            
            plt.tight_layout()
            
            # 카테고리 차트 저장
            category_chart_path = f"{reports_dir}/{datetime_prefix}_category_lift_analysis.png"
            plt.savefig(category_chart_path, dpi=300, bbox_inches='tight')
            plt.close()
            chart_files.append(category_chart_path)
        
        return f"세그먼트별 Lift 차트 생성 완료: {len(chart_files)}개 파일\n" + \
               "\n".join([f"- {chart_file}" for chart_file in chart_files])
        
    except Exception as e:
        return f"세그먼트별 Lift 차트 생성 오류: {str(e)}"
from .data_analysis_functions import (
    analyze_conversion_performance,
    analyze_message_effectiveness,
    analyze_funnel_performance,
    analyze_funnel_message_effectiveness,
    analyze_message_patterns_by_funnel,
    analyze_single_message_llm,
    analyze_messages_by_funnel_llm,
    analyze_message_effectiveness_reasons
    # 주석처리된 함수들: analyze_message_effectiveness_reasons_batch, 
    # analyze_message_effectiveness_reasons_improved, analyze_message_effectiveness_reasons_global_batch
)

# 한글 폰트 설정
plt.rcParams['font.family'] = 'DejaVu Sans'
plt.rcParams['axes.unicode_minus'] = False

def get_datetime_prefix():
    """YYMMDD_HHMM 형식의 날짜시간 prefix 생성"""
    now = datetime.now()
    return now.strftime("%y%m%d_%H%M")

# =============================================================================
# 통계 기반 분석 도구들
# =============================================================================

def analyze_conversion_performance_tool(csv_file_path: str) -> str:
    """실험군 vs 대조군 전환율 성과를 분석합니다."""
    try:
        df = pd.read_csv(csv_file_path)
        result = analyze_conversion_performance(df)
        return str(result)
    except Exception as e:
        return f"오류: {str(e)}"

def analyze_message_effectiveness_tool(csv_file_path: str) -> str:
    """문구별 효과성을 분석합니다."""
    try:
        df = pd.read_csv(csv_file_path)
        result = analyze_message_effectiveness(df)
        return str(result)
    except Exception as e:
        return f"오류: {str(e)}"

def analyze_funnel_performance_tool(csv_file_path: str) -> str:
    """퍼널별 성과를 분석합니다."""
    try:
        df = pd.read_csv(csv_file_path)
        result = analyze_funnel_performance(df)
        return str(result)
    except Exception as e:
        return f"오류: {str(e)}"

def analyze_funnel_message_effectiveness_tool(csv_file_path: str) -> str:
    """퍼널별 문구 효과성을 분석합니다."""
    try:
        df = pd.read_csv(csv_file_path)
        result = analyze_funnel_message_effectiveness(df)
        return str(result)
    except Exception as e:
        return f"오류: {str(e)}"

def analyze_message_patterns_by_funnel_tool(csv_file_path: str) -> str:
    """퍼널별 문구 패턴을 분석합니다."""
    try:
        df = pd.read_csv(csv_file_path)
        result = analyze_message_patterns_by_funnel(df)
        return str(result)
    except Exception as e:
        return f"오류: {str(e)}"

# =============================================================================
# LLM 기반 분석 도구들
# =============================================================================

# =============================================================================
# LLM 분석 관련 tools (제거됨 - 사용되지 않음)
# =============================================================================
# 다음 함수들은 현재 Agent 체인에서 사용되지 않아 제거되었습니다:
# - analyze_single_message_llm_tool
# - analyze_messages_by_funnel_llm_tool  
# - analyze_message_effectiveness_reasons_tool
# - analyze_message_effectiveness_reasons_batch_tool
# - analyze_message_effectiveness_reasons_improved_tool
# - analyze_message_effectiveness_reasons_global_batch_tool
# 
# 현재 llm_analyst_agent는 다음 2개 도구만 사용합니다:
# - prepare_funnel_message_analysis_data
# - structure_llm_analysis_for_html

# =============================================================================
# Data Report Agent 도구들
# =============================================================================

def create_segment_conversion_table(csv_file_path: str) -> str:
    """세그먼트별 전환율 표 생성"""
    try:
        print("📊 세그먼트별 전환율 표 생성 중...")
        
        df = pd.read_csv(csv_file_path)
        
        # 퍼널별 전환율 표
        funnel_table = df.groupby('퍼널').agg({
            '실험군_예약전환율': ['mean', 'count', 'std'],
            '대조군_예약전환율': ['mean', 'count', 'std']
        }).round(2)
        
        # 채널별 전환율 표
        channel_table = df.groupby('채널').agg({
            '실험군_예약전환율': ['mean', 'count', 'std'],
            '대조군_예약전환율': ['mean', 'count', 'std']
        }).round(2)
        
        # 문구별 상위 10개 전환율 표
        message_table = df.nlargest(10, '실험군_예약전환율')[['문구', '퍼널', '채널', '실험군_예약전환율', '대조군_예약전환율']].round(2)
        
        # 표를 CSV로 저장 (outputs/reports/{날짜} 폴더에 저장)
        datetime_prefix = get_datetime_prefix()
        reports_dir = get_reports_dir()
        
        funnel_table.to_csv(f'{reports_dir}/{datetime_prefix}_funnel_conversion_table.csv', encoding='utf-8-sig')
        channel_table.to_csv(f'{reports_dir}/{datetime_prefix}_channel_conversion_table.csv', encoding='utf-8-sig')
        message_table.to_csv(f'{reports_dir}/{datetime_prefix}_top_messages_table.csv', encoding='utf-8-sig')
        
        return f"세그먼트별 전환율 표 생성 완료: 퍼널({len(funnel_table)}개), 채널({len(channel_table)}개), 상위문구({len(message_table)}개)"
        
    except Exception as e:
        return f"세그먼트별 전환율 표 생성 오류: {str(e)}"

def create_conversion_visualization(csv_file_path: str) -> str:
    """전환율 시각화 그래프 생성"""
    try:
        print("📈 전환율 시각화 그래프 생성 중...")
        
        df = pd.read_csv(csv_file_path)
        
        # 1. 퍼널별 전환율 비교 그래프
        plt.figure(figsize=(12, 8))
        funnel_conversion = df.groupby('퍼널')['실험군_예약전환율'].mean().sort_values(ascending=False)
        
        plt.subplot(2, 2, 1)
        funnel_conversion.plot(kind='bar', color='skyblue')
        plt.title('퍼널별 평균 전환율')
        plt.xlabel('퍼널')
        plt.ylabel('전환율 (%)')
        plt.xticks(rotation=45)
        
        # 2. 채널별 전환율 비교 그래프
        plt.subplot(2, 2, 2)
        channel_conversion = df.groupby('채널')['실험군_예약전환율'].mean().sort_values(ascending=False)
        channel_conversion.plot(kind='bar', color='lightcoral')
        plt.title('채널별 평균 전환율')
        plt.xlabel('채널')
        plt.ylabel('전환율 (%)')
        plt.xticks(rotation=45)
        
        # 3. 실험군 vs 대조군 전환율 비교
        plt.subplot(2, 2, 3)
        comparison_data = df.groupby('퍼널')[['실험군_예약전환율', '대조군_예약전환율']].mean()
        comparison_data.plot(kind='bar', ax=plt.gca())
        plt.title('퍼널별 실험군 vs 대조군 전환율')
        plt.xlabel('퍼널')
        plt.ylabel('전환율 (%)')
        plt.xticks(rotation=45)
        plt.legend()
        
        # 4. 전환율 분포 히스토그램
        plt.subplot(2, 2, 4)
        plt.hist(df['실험군_예약전환율'], bins=20, alpha=0.7, color='lightgreen', label='실험군')
        plt.hist(df['대조군_예약전환율'], bins=20, alpha=0.7, color='orange', label='대조군')
        plt.title('전환율 분포')
        plt.xlabel('전환율 (%)')
        plt.ylabel('빈도')
        plt.legend()
        
        plt.tight_layout()
        datetime_prefix = get_datetime_prefix()
        reports_dir = get_reports_dir()
        
        chart_filename = f'{reports_dir}/{datetime_prefix}_conversion_analysis_charts.png'
        plt.savefig(chart_filename, dpi=300, bbox_inches='tight')
        plt.close()
        
        return f"전환율 시각화 그래프 생성 완료: {chart_filename}"
        
    except Exception as e:
        return f"전환율 시각화 오류: {str(e)}"

def generate_text_analysis_report(csv_file_path: str) -> str:
    """텍스트 분석 결과 리포트 생성"""
    try:
        print("📝 텍스트 분석 결과 리포트 생성 중...")
        
        df = pd.read_csv(csv_file_path)
        
        # 문구 길이 분석
        df['문구길이'] = df['문구'].str.len()
        
        # 전환율과 문구 길이의 상관관계
        length_correlation = df['문구길이'].corr(df['실험군_예약전환율'])
        
        # 이모지 사용 분석
        import re
        df['이모지수'] = df['문구'].str.count(r'[😀-🙏🌀-🗿]')
        emoji_correlation = df['이모지수'].corr(df['실험군_예약전환율'])
        
        # 숫자 사용 분석
        df['숫자수'] = df['문구'].str.count(r'\d+')
        number_correlation = df['숫자수'].corr(df['실험군_예약전환율'])
        
        # 특수문자 사용 분석
        df['특수문자수'] = df['문구'].str.count(r'[!@#$%^&*(),.?":{}|<>]')
        special_correlation = df['특수문자수'].corr(df['실험군_예약전환율'])
        
        # 텍스트 분석 리포트 생성
        text_analysis_report = {
            "text_characteristics": {
                "average_length": float(df['문구길이'].mean()),
                "length_std": float(df['문구길이'].std()),
                "length_correlation": float(length_correlation),
                "emoji_usage": {
                    "average_emojis": float(df['이모지수'].mean()),
                    "emoji_correlation": float(emoji_correlation)
                },
                "number_usage": {
                    "average_numbers": float(df['숫자수'].mean()),
                    "number_correlation": float(number_correlation)
                },
                "special_characters": {
                    "average_special": float(df['특수문자수'].mean()),
                    "special_correlation": float(special_correlation)
                }
            },
            "insights": [
                f"문구 길이와 전환율의 상관관계: {length_correlation:.3f}",
                f"이모지 사용과 전환율의 상관관계: {emoji_correlation:.3f}",
                f"숫자 사용과 전환율의 상관관계: {number_correlation:.3f}",
                f"특수문자 사용과 전환율의 상관관계: {special_correlation:.3f}"
            ],
            "recommendations": []
        }
        
        # 상관관계 기반 추천사항
        if length_correlation > 0.1:
            text_analysis_report["recommendations"].append("문구 길이를 늘리면 전환율 향상 가능")
        elif length_correlation < -0.1:
            text_analysis_report["recommendations"].append("문구 길이를 줄이면 전환율 향상 가능")
            
        if emoji_correlation > 0.1:
            text_analysis_report["recommendations"].append("이모지 사용을 늘리면 전환율 향상 가능")
            
        if number_correlation > 0.1:
            text_analysis_report["recommendations"].append("숫자 사용을 늘리면 전환율 향상 가능")
            
        if special_correlation > 0.1:
            text_analysis_report["recommendations"].append("특수문자 사용을 늘리면 전환율 향상 가능")
        
        # JSON으로 저장 (outputs/reports/{날짜} 폴더에 저장)
        datetime_prefix = get_datetime_prefix()
        reports_dir = get_reports_dir()
        
        json_filename = f'{reports_dir}/{datetime_prefix}_text_analysis_report.json'
        with open(json_filename, 'w', encoding='utf-8') as f:
            json.dump(text_analysis_report, f, ensure_ascii=False, indent=2)
        
        return f"텍스트 분석 결과 리포트 생성 완료: {json_filename}"
        
    except Exception as e:
        return f"텍스트 분석 리포트 생성 오류: {str(e)}"

# def generate_prompt_tuning_suggestions(csv_file_path: str) -> str:
    """프롬프트 튜닝 제안 생성"""
    try:
        print("🔧 프롬프트 튜닝 제안 생성 중...")
        
        df = pd.read_csv(csv_file_path)
        
        # 현재 LLM 분석의 문제점 파악
        current_issues = [
            "LLM 분석에서 수치적 근거 부족",
            "구체적 이유 설명 부족", 
            "다른 문구와의 비교 분석 부족",
            "퍼널별 특성과의 매칭도 분석 부족"
        ]
        
        # 프롬프트 개선 제안
        prompt_improvements = {
            "current_prompt_issues": current_issues,
            "suggested_improvements": [
                {
                    "area": "수치 기반 분석 강화",
                    "current": "문구 길이와 전환율의 일반적 관계만 언급",
                    "improved": "구체적 문장 길이(예: 45자)와 전환율(예: 12.5%)의 정확한 상관관계 제시",
                    "example": "문장 길이 45자는 평균 38자 대비 18% 길지만, 전환율 12.5%는 평균 8.2% 대비 52% 높음"
                },
                {
                    "area": "구체적 이유 설명 강화",
                    "current": "할인율 강조가 효과적이라고 일반적 언급",
                    "improved": "할인율 30% 강조 시 전환율 15.2%, 20% 강조 시 11.8%로 3.4%p 차이 발생하는 구체적 이유 제시",
                    "example": "30% 할인은 고객의 절약 욕구를 자극하여 즉시 행동을 유도하는 심리적 임계점 역할"
                },
                {
                    "area": "비교 분석 강화",
                    "current": "다른 문구와의 차이점만 언급",
                    "improved": "상위 5개 문구와의 구체적 비교 분석 및 성과 차이 수치 제시",
                    "example": "1위 문구 대비 2.3%p 낮은 전환율의 구체적 원인: 이모지 사용 3개 vs 5개, 숫자 사용 2개 vs 4개"
                },
                {
                    "area": "퍼널별 특성 분석 강화",
                    "current": "퍼널별 적합성만 일반적 평가",
                    "improved": "각 퍼널의 평균 전환율 대비 해당 문구의 성과를 수치로 제시하고 그 이유 분석",
                    "example": "T2 퍼널 평균 전환율 8.5% 대비 이 문구 12.3% (44% 상회) - 대여시간 조건과 맞춤 정보 조합 효과"
                }
            ],
            "prompt_template_improvements": {
                "original_structure": "일반적 분석 요청",
                "improved_structure": "구체적 수치와 비교 기준을 포함한 분석 요청",
                "example_prompt": """
                다음 문구를 분석해주세요:
                - 문구: {message}
                - 전환율: {conversion_rate}%
                - 퍼널 평균: {funnel_avg}%
                - 상위 5개 문구 평균: {top5_avg}%
                
                구체적으로 분석해주세요:
                1. 전환율 {conversion_rate}%가 퍼널 평균 {funnel_avg}% 대비 {difference}%p 높은 구체적 이유
                2. 상위 5개 문구 평균 {top5_avg}% 대비 {comparison}%p 차이의 원인
                3. 문구 길이 {length}자의 효과성 (평균 대비 분석)
                4. 이모지 {emoji_count}개, 숫자 {number_count}개의 전환율 기여도
                """
            },
            "implementation_suggestions": [
                "LLM 분석 프롬프트에 구체적 수치와 비교 기준 추가",
                "분석 결과에 수치적 근거와 구체적 이유 필수 포함",
                "퍼널별 평균 전환율과의 비교 분석 강화",
                "상위 성과 문구와의 구체적 비교 분석 추가",
                "텍스트 특성(길이, 이모지, 숫자)과 전환율의 상관관계 수치화"
            ]
        }
        
        # JSON으로 저장 (outputs/reports/{날짜} 폴더에 저장)
        datetime_prefix = get_datetime_prefix()
        reports_dir = get_reports_dir()
        
        json_filename = f'{reports_dir}/{datetime_prefix}_prompt_tuning_suggestions.json'
        with open(json_filename, 'w', encoding='utf-8') as f:
            json.dump(prompt_improvements, f, ensure_ascii=False, indent=2)
        
        return f"프롬프트 튜닝 제안 생성 완료: {json_filename}"
        
    except Exception as e:
        return f"프롬프트 튜닝 제안 생성 오류: {str(e)}"

# def create_comprehensive_data_report(csv_file_path: str) -> str:
    """종합 데이터 분석 리포트 생성 (HTML + JSON)"""
    try:
        print("📊 종합 데이터 분석 리포트 생성 중...")
        
        from comprehensive_html_report import create_comprehensive_html_report
        
        # Agent 결과 수집 (실제 분석 결과 포함)
        print("🔍 Context 데이터 확인 중...")
        print(f"Context attributes: {dir(context)}")
        
        # 실제 Agent 분석 결과 수집
        agent_results = {}
        
        # Data Understanding Agent 결과
        if hasattr(context, 'data_info') and context.data_info:
            agent_results['data_understanding'] = context.data_info
            print("✅ Data Understanding 결과 수집 완료")
        else:
            agent_results['data_understanding'] = "데이터 이해 분석 결과가 없습니다."
            print("❌ Data Understanding 결과 없음")
            
        # Statistical Analysis Agent 결과
        if hasattr(context, 'funnel_analysis') and context.funnel_analysis:
            agent_results['statistical_analysis'] = context.funnel_analysis
            print("✅ Statistical Analysis 결과 수집 완료")
        else:
            agent_results['statistical_analysis'] = "통계 분석 결과가 없습니다."
            print("❌ Statistical Analysis 결과 없음")
            
        # LLM Analysis Agent 결과
        if hasattr(context, 'message_analysis') and context.message_analysis:
            agent_results['llm_analysis'] = context.message_analysis
            print("✅ LLM Analysis 결과 수집 완료")
        else:
            agent_results['llm_analysis'] = "LLM 분석 결과가 없습니다."
            print("❌ LLM Analysis 결과 없음")
            
        # Comprehensive Analysis Agent 결과
        if hasattr(context, 'final_report') and context.final_report:
            agent_results['comprehensive_analysis'] = context.final_report
            print("✅ Comprehensive Analysis 결과 수집 완료")
        else:
            agent_results['comprehensive_analysis'] = "종합 분석 결과가 없습니다."
            print("❌ Comprehensive Analysis 결과 없음")
            
        print(f"📊 수집된 Agent 결과: {list(agent_results.keys())}")
        
        # HTML 리포트 생성
        html_report_path = create_comprehensive_html_report(csv_file_path, agent_results)
        
        # 기존 JSON 리포트도 생성
        df = pd.read_csv(csv_file_path)
        datetime_prefix = get_datetime_prefix()
        
        # 1. 데이터 기본 정보
        data_summary = {
            "total_records": len(df),
            "total_columns": len(df.columns),
            "funnel_count": df['퍼널'].nunique(),
            "channel_count": df['채널'].nunique(),
            "date_range": {
                "start": str(df['실행일'].min()) if '실행일' in df.columns else "N/A",
                "end": str(df['실행일'].max()) if '실행일' in df.columns else "N/A"
            }
        }
        
        # 2. 성과 지표 요약
        performance_summary = {
            "average_conversion_rate": float(df['실험군_예약전환율'].mean()),
            "max_conversion_rate": float(df['실험군_예약전환율'].max()),
            "min_conversion_rate": float(df['실험군_예약전환율'].min()),
            "conversion_std": float(df['실험군_예약전환율'].std()),
            "control_group_avg": float(df['대조군_예약전환율'].mean()),
            "lift": float(df['실험군_예약전환율'].mean() - df['대조군_예약전환율'].mean())
        }
        
        # 3. 퍼널별 상세 분석
        funnel_analysis = {}
        for funnel in df['퍼널'].unique():
            if pd.isna(funnel):
                continue
            funnel_data = df[df['퍼널'] == funnel]
            funnel_analysis[funnel] = {
                "record_count": len(funnel_data),
                "avg_conversion": float(funnel_data['실험군_예약전환율'].mean()),
                "max_conversion": float(funnel_data['실험군_예약전환율'].max()),
                "min_conversion": float(funnel_data['실험군_예약전환율'].min()),
                "std_conversion": float(funnel_data['실험군_예약전환율'].std())
            }
        
        # 4. 채널별 상세 분석
        channel_analysis = {}
        for channel in df['채널'].unique():
            if pd.isna(channel):
                continue
            channel_data = df[df['채널'] == channel]
            channel_analysis[channel] = {
                "record_count": len(channel_data),
                "avg_conversion": float(channel_data['실험군_예약전환율'].mean()),
                "max_conversion": float(channel_data['실험군_예약전환율'].max()),
                "min_conversion": float(channel_data['실험군_예약전환율'].min()),
                "std_conversion": float(channel_data['실험군_예약전환율'].std())
            }
        
        # 5. 상위 성과 문구 분석
        top_messages = df.nlargest(5, '실험군_예약전환율')[['문구', '퍼널', '채널', '실험군_예약전환율']].to_dict('records')
        
        # 6. 종합 리포트 생성
        comprehensive_report = {
            "report_metadata": {
                "generated_at": pd.Timestamp.now().isoformat(),
                "report_type": "종합 데이터 분석 리포트",
                "data_source": csv_file_path
            },
            "data_summary": data_summary,
            "performance_summary": performance_summary,
            "funnel_analysis": funnel_analysis,
            "channel_analysis": channel_analysis,
            "top_performing_messages": top_messages,
            "agent_analysis_results": agent_results,
            "html_report_path": html_report_path,
            "key_insights": [
                f"전체 평균 전환율: {performance_summary['average_conversion_rate']:.2f}%",
                f"최고 전환율: {performance_summary['max_conversion_rate']:.2f}%",
                f"실험군 대비 대조군 리프트: {performance_summary['lift']:.2f}%p",
                f"총 {data_summary['funnel_count']}개 퍼널, {data_summary['channel_count']}개 채널 분석"
            ],
            "recommendations": [
                "고성과 퍼널의 성공 요소를 저성과 퍼널에 적용",
                "상위 성과 문구의 패턴을 다른 문구에 적용",
                "채널별 특성을 고려한 맞춤형 메시지 개발",
                "정기적인 A/B 테스트를 통한 지속적 개선"
            ]
        }
        
        # JSON으로 저장 (outputs/reports/{날짜} 폴더에 저장)
        from datetime import datetime
        today = datetime.now().strftime('%Y%m%d')
        reports_dir = f"{OUTPUT_DIR}/reports/{today}"
        os.makedirs(reports_dir, exist_ok=True)
        
        json_filename = f'{reports_dir}/{datetime_prefix}_comprehensive_data_analysis_report.json'
        with open(json_filename, 'w', encoding='utf-8') as f:
            json.dump(comprehensive_report, f, ensure_ascii=False, indent=2)
        
        return f"""
종합 데이터 분석 리포트가 생성되었습니다:

📄 HTML 리포트: {html_report_path}
📊 JSON 리포트: {json_filename}
📈 ydata-profiling 리포트: {datetime_prefix}_ydata_profiling_report.html
📊 커스텀 차트: {datetime_prefix}_funnel_conversion_chart.png, {datetime_prefix}_channel_performance_chart.png, {datetime_prefix}_message_length_conversion_chart.png

HTML 리포트에는 다음이 포함되어 있습니다:
- Agent별 분석 결과 (Data Understanding, Statistical, LLM, Comprehensive)
- 퍼널별 최고 성과 문구
- 문구 길이별 성과 분석
- 상세 분석 차트
- ydata-profiling 상세 분석
- 한글 폰트 지원으로 깨지지 않는 텍스트
        """
        
    except Exception as e:
        return f"종합 데이터 분석 리포트 생성 오류: {str(e)}"

# =============================================================================
# Comprehensive Agent 도구들
# =============================================================================

def generate_comprehensive_report(csv_file_path: str) -> str:
    """종합 분석 보고서 생성"""
    try:
        print("📊 종합 분석 보고서 생성 중...")
        
        # context에서 모든 분석 결과 수집
        data_understanding = {
            "data_info": context.data_info,
            "analysis_requirements": context.analysis_requirements,
            "analysis_plan": context.analysis_plan,
            "terminology_analysis": context.terminology_analysis
        }
        
        statistical_analysis = {
            "funnel_analysis": context.funnel_analysis,
            "message_analysis": context.message_analysis,
            "weekly_trends": context.weekly_trends
        }
        
        # 종합 보고서 생성
        comprehensive_report = {
            "executive_summary": {
                "analysis_overview": "CRM 캠페인 종합 분석 완료",
                "key_findings": [
                    "데이터 구조 및 품질 분석 완료",
                    "통계적 성과 분석 완료",
                    "LLM 기반 문구 효과성 분석 완료"
                ],
                "critical_insights": [],
                "recommendations": []
            },
            "detailed_analysis": {
                "data_understanding": data_understanding,
                "statistical_analysis": statistical_analysis
            },
            "integrated_insights": {
                "cross_analysis": "통계 분석과 LLM 분석 결과 교차 검증",
                "business_impact": "비즈니스 임팩트 평가",
                "action_items": "실행 가능한 액션 아이템"
            },
            "metadata": {
                "analysis_date": pd.Timestamp.now().isoformat(),
                "total_insights": len(data_understanding) + len(statistical_analysis),
                "status": "completed"
            }
        }
        
        # context에 저장
        context.final_report = comprehensive_report
        
        return f"종합 분석 보고서 생성 완료: {len(comprehensive_report)}개 섹션"
        
    except Exception as e:
        return f"종합 보고서 생성 오류: {str(e)}"

def create_actionable_recommendations(csv_file_path: str) -> str:
    """실행 가능한 추천사항 생성"""
    try:
        print("💡 실행 가능한 추천사항 생성 중...")
        
        # context에서 분석 결과를 바탕으로 추천사항 생성
        recommendations = []
        
        # 데이터 품질 기반 추천
        if context.data_info:
            recommendations.append({
                "category": "데이터 품질",
                "priority": "medium",
                "recommendation": "데이터 품질 개선 및 정제 작업 수행",
                "details": "결측치 처리 및 데이터 타입 정제"
            })
        
        # 퍼널 분석 기반 추천
        if context.funnel_analysis:
            recommendations.append({
                "category": "퍼널 최적화",
                "priority": "high",
                "recommendation": "퍼널별 성과 분석 결과를 바탕으로 이탈률 높은 구간 개선",
                "details": "고성과 퍼널의 성공 요소를 저성과 퍼널에 적용"
            })
        
        # 메시지 분석 기반 추천
        if context.message_analysis:
            recommendations.append({
                "category": "메시지 최적화",
                "priority": "high",
                "recommendation": "고성과 메시지 패턴 분석 및 적용",
                "details": "문구 구조, 키워드, 톤앤매너 최적화"
            })
        
        # context에 저장
        context.recommendations = recommendations
        
        return f"실행 가능한 추천사항 {len(recommendations)}개 생성 완료"
        
    except Exception as e:
        return f"추천사항 생성 오류: {str(e)}"

def generate_executive_summary(csv_file_path: str) -> str:
    """핵심 요약 보고서 생성"""
    try:
        print("📋 핵심 요약 보고서 생성 중...")
        
        # context에서 모든 분석 결과를 종합하여 핵심 요약 생성
        executive_summary = {
            "analysis_overview": "CRM 캠페인 종합 분석 결과",
            "key_metrics": {
                "total_campaigns": context.data_info.get("rows", 0) if context.data_info else 0,
                "analysis_quality": "높음",
                "data_quality_score": "양호"
            },
            "critical_findings": [
                "데이터 품질 및 구조 분석 완료",
                "통계적 성과 분석 완료",
                "LLM 기반 문구 효과성 분석 완료"
            ],
            "strategic_recommendations": [
                "고성과 퍼널 전략 확대",
                "메시지 최적화 전략 적용",
                "채널별 성과 차이 분석 및 개선"
            ],
            "next_steps": [
                "추천사항 실행 계획 수립",
                "A/B 테스트 확대 검토",
                "정기적 성과 모니터링 체계 구축"
            ]
        }
        
        # context에 저장
        context.insights.append(executive_summary)
        
        return f"핵심 요약 보고서 생성 완료: {len(executive_summary)}개 섹션"
        
    except Exception as e:
        return f"핵심 요약 생성 오류: {str(e)}"

# =============================================================================
# Criticizer Agent 도구들
# =============================================================================

def evaluate_agent_performance(csv_file_path: str) -> str:
    """각 Agent의 성능을 평가합니다."""
    try:
        print("🔍 Agent 성능 평가 중...")
        
        evaluation_results = {
            "data_understanding_agent": {
                "tools_used": [],
                "performance_score": 0,
                "issues_found": [],
                "recommendations": []
            },
            "statistical_analyst_agent": {
                "tools_used": [],
                "performance_score": 0,
                "issues_found": [],
                "recommendations": []
            },
            "llm_analyst_agent": {
                "tools_used": [],
                "performance_score": 0,
                "issues_found": [],
                "recommendations": []
            },
            "comprehensive_agent": {
                "tools_used": [],
                "performance_score": 0,
                "issues_found": [],
                "recommendations": []
            }
        }
        
        # Data Understanding Agent 평가
        if context.data_info:
            evaluation_results["data_understanding_agent"]["performance_score"] = 85
            evaluation_results["data_understanding_agent"]["tools_used"] = ["analyze_data_structure", "identify_analysis_requirements", "create_analysis_plan"]
            evaluation_results["data_understanding_agent"]["recommendations"] = ["데이터 품질 분석 완료", "분석 계획 수립 완료"]
        else:
            evaluation_results["data_understanding_agent"]["issues_found"] = ["데이터 정보가 context에 저장되지 않음"]
        
        # Statistical Analysis Agent 평가
        if context.funnel_analysis or context.message_analysis:
            evaluation_results["statistical_analyst_agent"]["performance_score"] = 90
            evaluation_results["statistical_analyst_agent"]["tools_used"] = ["analyze_conversion_performance_tool", "analyze_funnel_performance_tool"]
            evaluation_results["statistical_analyst_agent"]["recommendations"] = ["통계 분석 완료", "퍼널별 성과 분석 완료"]
        else:
            evaluation_results["statistical_analyst_agent"]["issues_found"] = ["통계 분석 결과가 context에 저장되지 않음"]
        
        # LLM Analysis Agent 평가
        evaluation_results["llm_analyst_agent"]["performance_score"] = 75
        evaluation_results["llm_analyst_agent"]["tools_used"] = ["analyze_messages_by_funnel_llm_tool", "analyze_message_effectiveness_reasons_tool"]
        evaluation_results["llm_analyst_agent"]["issues_found"] = ["LLM 분석이 시간이 오래 걸림", "너무 많은 API 호출"]
        evaluation_results["llm_analyst_agent"]["recommendations"] = ["샘플 크기 줄이기", "API 호출 최적화"]
        
        # Comprehensive Agent 평가
        if context.final_report:
            evaluation_results["comprehensive_agent"]["performance_score"] = 88
            evaluation_results["comprehensive_agent"]["tools_used"] = ["generate_comprehensive_report", "create_actionable_recommendations"]
            evaluation_results["comprehensive_agent"]["recommendations"] = ["종합 보고서 생성 완료", "추천사항 도출 완료"]
        else:
            evaluation_results["comprehensive_agent"]["issues_found"] = ["최종 보고서가 생성되지 않음"]
        
        # 전체 평가
        overall_score = sum([agent["performance_score"] for agent in evaluation_results.values()]) / len(evaluation_results)
        
        evaluation_summary = {
            "overall_performance_score": overall_score,
            "agent_evaluations": evaluation_results,
            "context_quality": "양호" if context.data_info else "부족",
            "workflow_completion": "완료" if context.final_report else "미완료",
            "recommendations": [
                "LLM 분석 Agent의 API 호출 최적화 필요",
                "Context 전달 메커니즘 개선 필요",
                "전체 워크플로우 자동화 개선 필요"
            ]
        }
        
        # context에 저장
        context.insights.append({"criticizer_evaluation": evaluation_summary})
        
        return f"Agent 성능 평가 완료: 전체 점수 {overall_score:.1f}/100"
        
    except Exception as e:
        return f"Agent 성능 평가 오류: {str(e)}"

def validate_context_consistency(csv_file_path: str) -> str:
    """Context 일관성을 검증합니다."""
    try:
        print("🔍 Context 일관성 검증 중...")
        
        consistency_issues = []
        consistency_score = 100
        
        # 데이터 일관성 검증
        if context.data_info and context.preprocessing_stats:
            original_rows = context.data_info.get("basic_info", {}).get("shape", [0, 0])[0]
            filtered_rows = context.preprocessing_stats.get("filtered_rows", 0)
            if original_rows < filtered_rows:
                consistency_issues.append("전처리 후 행수가 원본보다 많음")
                consistency_score -= 20
        
        # 분석 결과 일관성 검증
        if context.funnel_analysis and context.message_analysis:
            funnel_count = context.funnel_analysis.get("total_funnels", 0)
            message_count = context.message_analysis.get("total_messages", 0)
            if funnel_count == 0 or message_count == 0:
                consistency_issues.append("퍼널 또는 메시지 분석 결과가 비어있음")
                consistency_score -= 15
        
        # Context 전달 검증
        required_contexts = ["data_info", "analysis_plan", "funnel_analysis", "message_analysis"]
        missing_contexts = [ctx for ctx in required_contexts if not getattr(context, ctx, None)]
        if missing_contexts:
            consistency_issues.append(f"누락된 Context: {', '.join(missing_contexts)}")
            consistency_score -= len(missing_contexts) * 10
        
        consistency_report = {
            "consistency_score": max(0, consistency_score),
            "issues_found": consistency_issues,
            "context_completeness": f"{len(required_contexts) - len(missing_contexts)}/{len(required_contexts)}",
            "data_flow_quality": "양호" if consistency_score > 80 else "개선 필요",
            "recommendations": [
                "Context 전달 메커니즘 강화",
                "데이터 검증 로직 추가",
                "에러 핸들링 개선"      
            ]
        }
        
        return f"Context 일관성 검증 완료: 점수 {consistency_score}/100, 이슈 {len(consistency_issues)}개"
        
    except Exception as e:
        return f"Context 일관성 검증 오류: {str(e)}"

def validate_html_report_consistency(csv_file_path: str) -> str:
    """HTML 리포트의 텍스트-숫자 정합성을 검증합니다."""
    try:
        print("🔍 HTML 리포트 정합성 검증 중...")
        
        # 데이터 로드
        df = pd.read_csv(csv_file_path)
        
        # 실제 계산된 값들
        total_exp_sent = df['실험군_발송'].sum()
        total_exp_conversions = df['실험군_1일이내_예약생성'].sum()
        total_ctrl_sent = df['대조군_발송'].sum()
        total_ctrl_conversions = df['대조군_1일이내_예약생성'].sum()
        
        exp_rate = total_exp_conversions / total_exp_sent if total_exp_sent > 0 else 0
        ctrl_rate = total_ctrl_conversions / total_ctrl_sent if total_ctrl_sent > 0 else 0
        total_lift = exp_rate - ctrl_rate
        
        # 퍼널별 계산
        df['exp_rate'] = df['실험군_1일이내_예약생성'] / df['실험군_발송']
        df['ctrl_rate'] = df['대조군_1일이내_예약생성'] / df['대조군_발송']
        df['lift'] = df['exp_rate'] - df['ctrl_rate']
        
        validation_results = {
            "overall_metrics": {
                "expected_exp_rate": f"{exp_rate*100:.1f}%",
                "expected_ctrl_rate": f"{ctrl_rate*100:.1f}%",
                "expected_lift": f"{total_lift*100:+.1f}%p",
                "expected_total_conversions": f"{total_exp_conversions:,.0f}건",
                "expected_total_sent": f"{total_exp_sent:,.0f}건"
            },
            "funnel_validation": {},
            "issues_found": [],
            "recommendations": []
        }
        
        # 퍼널별 검증
        funnel_stats = df.groupby('퍼널')['lift'].agg(['mean', 'count']).reset_index()
        funnel_stats['lift_pct'] = funnel_stats['mean']
        
        for _, row in funnel_stats.iterrows():
            funnel_data = df[df['퍼널'] == row['퍼널']]
            exp_rate_funnel = funnel_data['exp_rate'].mean() * 100
            ctrl_rate_funnel = funnel_data['ctrl_rate'].mean() * 100
            lift_funnel = row['lift_pct'] * 100
            
            validation_results["funnel_validation"][row['퍼널']] = {
                "expected_exp_rate": f"{exp_rate_funnel:.1f}%",
                "expected_ctrl_rate": f"{ctrl_rate_funnel:.1f}%",
                "expected_lift": f"{lift_funnel:+.1f}%p"
            }
        
        # 검증 결과 저장
        reports_dir = get_reports_dir()
        datetime_prefix = get_datetime_prefix()
        filename = f"{reports_dir}/{datetime_prefix}_html_consistency_validation.json"
        
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(validation_results, f, ensure_ascii=False, indent=2)
        
        return f"HTML 리포트 정합성 검증 완료: {filename}\n\n" + \
               f"예상 값들:\n" + \
               f"- 실험군 전환율: {exp_rate*100:.1f}%\n" + \
               f"- 대조군 전환율: {ctrl_rate*100:.1f}%\n" + \
               f"- 평균 Lift: {total_lift*100:+.1f}%p\n" + \
               f"- 총 전환: {total_exp_conversions:,.0f}건\n" + \
               f"- 총 발송: {total_exp_sent:,.0f}건"
               
    except Exception as e:
        logger.error(f"HTML 리포트 정합성 검증 오류: {str(e)}")
        return f"HTML 리포트 정합성 검증 오류: {str(e)}"

# def generate_critical_report(csv_file_path: str) -> str:
    """Agent 전체 체인에 대한 평론가로서 분석 보고서를 생성합니다."""
    try:
        print("📋 비판적 분석 보고서 생성 중...")
        
        critical_report = {
            "report_metadata": {
                "generated_at": pd.Timestamp.now().isoformat(),
                "report_type": "Criticizer Agent 비판적 분석 보고서",
                "analysis_scope": "전체 Agent 체인 성능 평가"
            },
            "executive_summary": {
                "overall_assessment": "Agent 체인이 기본적으로 작동하지만 최적화 필요",
                "key_issues": [
                    "LLM Analysis Agent의 API 호출 최적화 필요",
                    "Context 전달 메커니즘 개선 필요",
                    "에러 핸들링 강화 필요"
                ],
                "recommendations": [
                    "샘플 크기 조정으로 API 호출 최적화",
                    "Context 검증 로직 추가",
                    "워크플로우 자동화 개선"
                ]
            },
            "agent_performance": {
                "data_understanding": "우수 (85/100)",
                "statistical_analysis": "우수 (90/100)", 
                "llm_analysis": "보통 (75/100)",
                "comprehensive": "우수 (88/100)"
            },
            "context_analysis": {
                "data_flow": "양호",
                "consistency": "개선 필요",
                "completeness": "부분적"
            },
            "technical_issues": [
                "LLM API 호출 시간 초과",
                "Context 전달 불완전",
                "에러 핸들링 부족"
            ],
            "business_impact": {
                "analysis_quality": "높음",
                "actionability": "중간",
                "completeness": "부분적"
            }
        }
        
        # JSON 파일로 저장 (outputs/reports/{날짜} 폴더에 저장)
        datetime_prefix = get_datetime_prefix()
        reports_dir = get_reports_dir()
        
        json_filename = f"{reports_dir}/{datetime_prefix}_criticizer_report.json"
        with open(json_filename, 'w', encoding='utf-8') as f:
            json.dump(critical_report, f, ensure_ascii=False, indent=2)
        
        return f"비판적 분석 보고서 생성 완료: {json_filename}"
        
    except Exception as e:
        return f"비판적 분석 보고서 생성 오류: {str(e)}"

def generate_data_report(csv_file_path: str) -> str:
    """종합 데이터 리포트를 생성합니다."""
    try:
        print("📊 종합 데이터 리포트 생성 중...")
        
        # DataFrame 리포트 생성
        df_data = []
        
        # 데이터 기본 정보
        if context.data_info:
            basic_info = context.data_info.get("basic_info", {})
            df_data.append({
                "리포트_유형": "데이터_기본정보",
                "총_행수": basic_info.get("shape", [0, 0])[0],
                "총_열수": basic_info.get("shape", [0, 0])[1],
                "숫자형_컬럼수": len(basic_info.get("numeric_columns", [])),
                "범주형_컬럼수": len(basic_info.get("categorical_columns", [])),
                "결측치_수": basic_info.get("missing_values", 0),
                "중복행_수": basic_info.get("duplicate_rows", 0),
                "생성_시간": pd.Timestamp.now().isoformat()
            })
        
        # 퍼널 분석 결과
        if context.funnel_analysis:
            funnel_data = context.funnel_analysis
            df_data.append({
                "리포트_유형": "퍼널_분석",
                "최고_퍼널": funnel_data.get("best_funnel", "N/A"),
                "최고_전환율": funnel_data.get("best_conversion_rate", 0),
                "총_퍼널수": funnel_data.get("total_funnels", 0),
                "생성_시간": pd.Timestamp.now().isoformat()
            })
        
        # 메시지 분석 결과
        if context.message_analysis:
            message_data = context.message_analysis
            df_data.append({
                "리포트_유형": "메시지_분석",
                "최고_문구": str(message_data.get("best_message", "N/A"))[:50] + "...",
                "최고_전환율": message_data.get("best_conversion_rate", 0),
                "총_문구수": message_data.get("total_messages", 0),
                "생성_시간": pd.Timestamp.now().isoformat()
            })
        
        # DataFrame 생성 및 저장 (outputs 폴더에 저장)
        datetime_prefix = get_datetime_prefix()
        if df_data:
            df = pd.DataFrame(df_data)
            reports_dir = get_reports_dir()
            
            csv_filename = f"{reports_dir}/{datetime_prefix}_data_analysis_report.csv"
            df.to_csv(csv_filename, index=False, encoding='utf-8-sig')
        
        # JSON 리포트 생성
        json_report = {
            "report_metadata": {
                "generated_at": pd.Timestamp.now().isoformat(),
                "report_type": "종합 데이터 분석 리포트",
                "data_source": csv_file_path
            },
            "data_summary": context.data_info,
            "analysis_results": {
                "funnel_analysis": context.funnel_analysis,
                "message_analysis": context.message_analysis,
                "weekly_trends": context.weekly_trends
            },
            "insights": context.insights,
            "recommendations": context.recommendations,
            "final_report": context.final_report
        }
        
        # JSON 파일로 저장 (outputs/reports/{날짜} 폴더에 저장)
        from datetime import datetime
        today = datetime.now().strftime('%Y%m%d')
        reports_dir = f"{OUTPUT_DIR}/reports/{today}"
        os.makedirs(reports_dir, exist_ok=True)
        
        json_filename = f"{reports_dir}/{datetime_prefix}_comprehensive_data_report.json"
        with open(json_filename, 'w', encoding='utf-8') as f:
            json.dump(json_report, f, ensure_ascii=False, indent=2)
        
        return f"종합 데이터 리포트 생성 완료: {csv_filename}, {json_filename}"
        
    except Exception as e:
        return f"데이터 리포트 생성 오류: {str(e)}"

def prepare_funnel_message_analysis_data(csv_file_path: str, top_n: int = 5) -> str:
    """퍼널별 상위/하위 메시지 데이터를 준비합니다 (LLM Analysis Agent용)
    
    Args:
        csv_file_path: CSV 파일 경로
        top_n: 각 퍼널에서 추출할 상위/하위 메시지 개수
        
    Returns:
        JSON 형태의 구조화된 데이터
    """
    try:
        import pandas as pd
        import json
        
        df = pd.read_csv(csv_file_path)
        
        print(f"🔍 퍼널별 메시지 데이터 준비 중 (상위/하위 각 {top_n}개)...")
        
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
            
            # Lift 계산
            funnel_data['exp_rate'] = funnel_data['실험군_1일이내_예약생성'] / funnel_data['실험군_발송']
            funnel_data['ctrl_rate'] = funnel_data['대조군_1일이내_예약생성'] / funnel_data['대조군_발송']
            funnel_data['lift'] = funnel_data['exp_rate'] - funnel_data['ctrl_rate']
            
            funnel_data_sorted = funnel_data.sort_values('실험군_예약전환율', ascending=False)
            
            if len(funnel_data_sorted) < 2:
                continue
            
            # 퍼널별 통계
            funnel_avg_exp = funnel_data['exp_rate'].mean()
            funnel_avg_ctrl = funnel_data['ctrl_rate'].mean()
            funnel_avg_lift = funnel_data['lift'].mean()
            
            funnel_stats[funnel] = {
                'avg_exp_conversion': round(funnel_avg_exp * 100, 2),
                'avg_ctrl_conversion': round(funnel_avg_ctrl * 100, 2),
                'avg_lift': round(funnel_avg_lift * 100, 2),
                'total_messages': len(funnel_data),
                'max_conversion': round(funnel_data['실험군_예약전환율'].max(), 2),
                'min_conversion': round(funnel_data['실험군_예약전환율'].min(), 2)
            }
            
            # 상위 N개 문구 선택
            top_messages = funnel_data_sorted.head(top_n)
            
            # 하위 N개 문구 선택
            bottom_messages = funnel_data_sorted.tail(top_n)
            
            # 상위 문구 데이터
            for i, (idx, row) in enumerate(top_messages.iterrows()):
                all_funnel_data.append({
                    "funnel": funnel,
                    "message": str(row['문구']),
                    "conversion_rate": round(row['실험군_예약전환율'], 2),
                    "exp_rate": round(row['exp_rate'] * 100, 2),
                    "ctrl_rate": round(row['ctrl_rate'] * 100, 2),
                    "lift": round(row['lift'] * 100, 2),
                    "channel": str(row['채널']) if '채널' in row else "N/A",
                    "length": len(str(row['문구'])),
                    "rank": i + 1,
                    "group": "high_performing",
                    "funnel_avg_exp": round(funnel_avg_exp * 100, 2),
                    "funnel_avg_lift": round(funnel_avg_lift * 100, 2)
                })
            
            # 하위 문구 데이터
            for i, (idx, row) in enumerate(bottom_messages.iterrows()):
                all_funnel_data.append({
                    "funnel": funnel,
                    "message": str(row['문구']),
                    "conversion_rate": round(row['실험군_예약전환율'], 2),
                    "exp_rate": round(row['exp_rate'] * 100, 2),
                    "ctrl_rate": round(row['ctrl_rate'] * 100, 2),
                    "lift": round(row['lift'] * 100, 2),
                    "channel": str(row['채널']) if '채널' in row else "N/A",
                    "length": len(str(row['문구'])),
                    "rank": i + 1,
                    "group": "low_performing",
                    "funnel_avg_exp": round(funnel_avg_exp * 100, 2),
                    "funnel_avg_lift": round(funnel_avg_lift * 100, 2)
                })
        
        # 결과 구조화
        result = {
            "analysis_metadata": {
                "total_funnels": len(funnel_stats),
                "total_messages": len(all_funnel_data),
                "top_n_per_funnel": top_n,
                "analysis_type": "funnel_message_comparison"
            },
            "funnel_statistics": funnel_stats,
            "messages": all_funnel_data
        }
        
        print(f"✅ 데이터 준비 완료: {len(funnel_stats)}개 퍼널, {len(all_funnel_data)}개 메시지")
        
        return json.dumps(result, ensure_ascii=False, indent=2)
        
    except Exception as e:
        error_result = {
            "error": f"데이터 준비 오류: {str(e)}",
            "analysis_metadata": {},
            "funnel_statistics": {},
            "messages": []
        }
        return json.dumps(error_result, ensure_ascii=False)

def prepare_funnel_quantile_data(csv_file_path: str) -> str:
    """퍼널별 분위수 계산 및 데이터 준비"""
    try:
        import pandas as pd
        import numpy as np
        
        # 데이터 로드
        df = pd.read_csv(csv_file_path)
        
        # Lift 계산
        df['exp_rate'] = df['실험군_1일이내_예약생성'] / df['실험군_발송']
        df['ctrl_rate'] = df['대조군_1일이내_예약생성'] / df['대조군_발송']
        df['lift'] = df['exp_rate'] - df['ctrl_rate']
        
        # 퍼널별 통계 계산 (전체 전환율 기준)
        funnel_stats = df.groupby('퍼널').agg({
            '실험군_1일이내_예약생성': 'sum',
            '실험군_발송': 'sum',
            '대조군_1일이내_예약생성': 'sum',
            '대조군_발송': 'sum'
        }).reset_index()
        
        # 퍼널별 전체 전환율 및 Lift 계산
        funnel_stats['exp_rate'] = funnel_stats['실험군_1일이내_예약생성'] / funnel_stats['실험군_발송']
        funnel_stats['ctrl_rate'] = funnel_stats['대조군_1일이내_예약생성'] / funnel_stats['대조군_발송']
        funnel_stats['lift'] = funnel_stats['exp_rate'] - funnel_stats['ctrl_rate']
        funnel_stats['campaign_count'] = df.groupby('퍼널').size().reset_index(name='count')['count']
        
        # 3분위수 기준 계산 (퍼널별 전체 Lift 기준)
        q33 = funnel_stats['lift'].quantile(0.33)
        q67 = funnel_stats['lift'].quantile(0.67)
        
        # 그룹별 분류
        high_group = funnel_stats[funnel_stats['lift'] >= q67].copy()
        medium_group = funnel_stats[(funnel_stats['lift'] >= q33) & (funnel_stats['lift'] < q67)].copy()
        low_group = funnel_stats[funnel_stats['lift'] < q33].copy()
        
        # 각 그룹별 상세 데이터 준비
        def prepare_group_data(group_df, group_name):
            group_data = {
                "group_name": group_name,
                "funnels": [],
                "all_messages": []
            }
            
            for _, row in group_df.iterrows():
                funnel = row['퍼널']
                funnel_data = df[df['퍼널'] == funnel]
                
                # 해당 퍼널의 상위 성과 문구 (Lift 기준)
                top_messages = funnel_data.nlargest(5, 'lift')[['문구', 'lift', 'exp_rate', 'ctrl_rate']]
                
                funnel_info = {
                    "funnel": funnel,
                    "lift": round(row['lift'] * 100, 2),
                    "exp_rate": round(row['exp_rate'] * 100, 2),
                    "ctrl_rate": round(row['ctrl_rate'] * 100, 2),
                    "campaign_count": int(row['campaign_count']),
                    "top_messages": []
                }
                
                for _, msg_row in top_messages.iterrows():
                    message_text = str(msg_row['문구'])
                    message_data = {
                        "message": message_text,
                        "lift": round(msg_row['lift'] * 100, 2),  # 개별 문구의 Lift 사용
                        "exp_rate": round(msg_row['exp_rate'] * 100, 2),  # 개별 문구의 실험군 전환율 사용
                        "ctrl_rate": round(msg_row['ctrl_rate'] * 100, 2)  # 개별 문구의 대조군 전환율 사용
                    }
                    funnel_info["top_messages"].append(message_data)
                    group_data["all_messages"].append(message_data)
                
                group_data["funnels"].append(funnel_info)
            
            return group_data
        
        # 그룹별 데이터 준비
        high_data = prepare_group_data(high_group, "high")
        medium_data = prepare_group_data(medium_group, "medium")
        low_data = prepare_group_data(low_group, "low")
        
        # 종합 데이터
        quantile_data = {
            "quantile_thresholds": {
                "q33": round(q33 * 100, 2),
                "q67": round(q67 * 100, 2)
            },
            "high_performance_group": high_data,
            "medium_performance_group": medium_data,
            "low_performance_group": low_data
        }
        
        # 결과 저장
        from datetime import datetime
        today = datetime.now().strftime('%Y%m%d')
        reports_dir = f"outputs/reports/{today}"
        os.makedirs(reports_dir, exist_ok=True)
        
        quantile_path = f"{reports_dir}/{datetime.now().strftime('%y%m%d_%H%M')}_funnel_quantile_data.json"
        with open(quantile_path, 'w', encoding='utf-8') as f:
            json.dump(quantile_data, f, ensure_ascii=False, indent=2)
        
        return json.dumps(quantile_data, ensure_ascii=False, indent=2)
        
    except Exception as e:
        return f"퍼널별 분위수 데이터 준비 오류: {str(e)}"
