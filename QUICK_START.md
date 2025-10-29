# 빠른 시작 가이드

> **5분 안에 시작하기**

*by saintwo*

---

## 🚀 5분 설정

### 1. 사전 요구사항 확인
```bash
# Python 버전 확인 (3.11+ 필요)
python --version

# UV 설치 확인
uv --version
```

### 2. 의존성 설치
```bash
cd crm-analysis-agent
uv sync
```

### 3. API 구성
```bash
# 환경 템플릿 복사
cp env.example .env

# Azure OpenAI 자격 증명으로 .env 편집
nano .env
```

### 4. 분석 실행
```bash
uv run main.py
```

### 5. 결과 보기
```bash
# 생성된 HTML 보고서 열기
open outputs/reports/$(date +%Y%m%d)/*_comprehensive_data_analysis_report.html
```

---

## 📊 얻을 수 있는 것

- **경영진 요약**: 고수준 인사이트 및 권장사항
- **통계적 분석**: 전환율 및 리프트 계산
- **LLM 인사이트**: 메시지 효과성 분석
- **실행 가능한 권장사항**: 데이터 기반 마케팅 전략

---

## 🔧 문제 해결

### 일반적인 문제

**API 연결 실패**
```bash
# .env 파일 확인
cat .env | grep AZURE_OPENAI
```

**의존성 누락**
```bash
# 의존성 재설치
uv sync --reinstall
```

**데이터 형식 오류**
```bash
# CSV 파일 구조 확인
head -5 data/raw/*.csv
```

---

*빠른 시작 가이드 by saintwo*