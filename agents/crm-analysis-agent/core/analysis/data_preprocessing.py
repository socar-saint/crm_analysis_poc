"""데이터 전처리 함수들"""

import pandas as pd
import numpy as np
from typing import Dict, Any, List

def clean_numeric_columns(df, columns_to_clean):
    """
    숫자 컬럼에서 쉼표(,)와 퍼센트(%) 기호를 제거하고 float 타입으로 변환
    
    Parameters:
    df (pd.DataFrame): 원본 데이터프레임
    columns_to_clean (list): 정제할 컬럼명 리스트
    
    Returns:
    pd.DataFrame: 정제된 데이터프레임
    """
    df_cleaned = df.copy()
    
    for col in columns_to_clean:
        if col in df_cleaned.columns:
            # 1. 쉼표(,) 제거
            df_cleaned[col] = df_cleaned[col].astype(str).str.replace(',', '')
            
            # 2. 퍼센트(%) 제거
            df_cleaned[col] = df_cleaned[col].astype(str).str.replace('%', '')
            
            # 3. 공백 제거
            df_cleaned[col] = df_cleaned[col].astype(str).str.strip()
            
            # 4. 빈 문자열이나 'nan'을 NaN으로 변환
            df_cleaned[col] = df_cleaned[col].replace(['', 'nan', 'NaN'], np.nan)
            
            # 5. float 타입으로 변환
            df_cleaned[col] = pd.to_numeric(df_cleaned[col], errors='coerce')
    
    return df_cleaned

def preprocess_sales_data(df, numeric_columns):
    """
    세일즈 TF 액션 데이터 전처리
    
    Parameters:
    df (pd.DataFrame): 원본 데이터프레임
    numeric_columns (list): 정제할 숫자 컬럼명 리스트
    
    Returns:
    pd.DataFrame: 전처리된 데이터프레임
    """
    # 숫자 컬럼 정제
    df_cleaned = clean_numeric_columns(df, numeric_columns)
    
    # 발송량 500개 이상 필터링
    if '발송' in df_cleaned.columns:
        original_count = len(df_cleaned)
        df_cleaned = df_cleaned[df_cleaned['발송'] >= 500]
        filtered_count = len(df_cleaned)
        print(f"필터링 결과: {original_count}행 → {filtered_count}행")
    
    if '실행일' in df_cleaned.columns:
        # '8/18' → '2025-08-18' 형식으로 변환
        df_cleaned['실행일'] = pd.to_datetime(
            '2025/' + df_cleaned['실행일'].astype(str), 
            format='%Y/%m/%d', 
            errors='coerce'
        ).dt.strftime('%Y-%m-%d')
        
    return df_cleaned
        
def rename_columns_with_prefix(df):
    """
    실험군/대조군 컬럼에 prefix 추가
    
    Parameters:
    df (pd.DataFrame): 원본 데이터프레임
    
    Returns:
    pd.DataFrame: 컬럼명이 변경된 데이터프레임
    """
    df_renamed = df.copy()
    
    # 실험군 컬럼들 변경
    experiment_columns = {
        '발송': '실험군_발송',
        '1일이내 예약생성': '실험군_1일이내_예약생성',
        '예약전환율': '실험군_예약전환율',
        '3일이내 예약생성': '실험군_3일이내_예약생성',
        '예약전환율.1': '실험군_3일이내_예약전환율',
        '7일이내 예약생성': '실험군_7일이내_예약생성',
        '예약전환율.2': '실험군_7일이내_예약전환율'
    }
    
    # 대조군 컬럼들 변경
    control_columns = {
        '발송.1': '대조군_발송',
        '1일이내 예약생성.1': '대조군_1일이내_예약생성',
        '예약전환율.3': '대조군_예약전환율'
    }
    
    # 실험군 컬럼명 변경
    for old_name, new_name in experiment_columns.items():
        if old_name in df_renamed.columns:
            df_renamed = df_renamed.rename(columns={old_name: new_name})
    
    # 대조군 컬럼명 변경
    for old_name, new_name in control_columns.items():
        if old_name in df_renamed.columns:
            df_renamed = df_renamed.rename(columns={old_name: new_name})
    
    return df_renamed

def preprocess_crm_data(file_path: str) -> Dict[str, Any]:
    """
    CRM 데이터 전처리 통합 함수
    
    Parameters:
    file_path (str): CSV 파일 경로
    
    Returns:
    Dict[str, Any]: 전처리 결과
    """
    try:
        # 1. 데이터 로드
        df = pd.read_csv(file_path)
        print(f"원본 데이터: {df.shape[0]}행 x {df.shape[1]}열")
        
        # 2. 정제할 숫자 컬럼들 정의
        numeric_columns = [
            '발송', '1일이내 예약생성', '예약전환율', 
            '3일이내 예약생성', '예약전환율.1', 
            '7일이내 예약생성', '예약전환율.2',
            '발송.1', '1일이내 예약생성.1', '예약전환율.3'
        ]
        
        # 3. 데이터 전처리
        cleaned_df = preprocess_sales_data(df, numeric_columns)
        
        # 4. 컬럼명 변경
        final_df = rename_columns_with_prefix(cleaned_df)
        
        # 5. 전처리된 데이터 저장
        output_path = 'preprocessed_crm_data.csv'
        final_df.to_csv(output_path, index=False)
        
        return {
            "status": "success",
            "original_shape": df.shape,
            "final_shape": final_df.shape,
            "preprocessed_file_path": output_path,
            "message": f"전처리 완료: {df.shape[0]}행 → {final_df.shape[0]}행"
        }
        
    except Exception as e:
        return {
            "status": "error",
            "error_message": f"전처리 중 오류: {str(e)}"
        }

