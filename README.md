# Financial AI Agent

AI 에이전트가 **시장(거시경제) → 산업 → 개별 종목** 3단계로 투자 리서치를 동적으로 수행하는 Streamlit 웹 애플리케이션입니다. 고정된 리포트 템플릿 대신, 조회 시점의 데이터를 바탕으로 LLM이 그때그때 중요한 포인트를 판단해 분석합니다.

## 주요 기능

- **Macro 탭**: 거시경제 지표 기반 시장 국면 분석
- **Industry 탭**: 산업/섹터 상대강도 분석
- **Company 탭**: 개별 종목 펀더멘털 + 기술적 분석
- **News 탭**: 관련 뉴스 요약
- LLM이 생성하는 최종 투자 리포트 및 채팅 기반 Q&A

## 기술 스택

- **Framework**: Streamlit
- **Data**: Alpha Vantage API, yfinance, FRED API
- **LLM**: OpenAI API
- **Visualization**: Plotly, Altair

## 로컬 실행 방법

```bash
# 1. 가상환경 생성 및 활성화
python -m venv .venv
.venv\Scripts\activate        # Windows
# source .venv/bin/activate    # macOS/Linux

# 2. 패키지 설치
pip install -r requirements.txt

# 3. 환경변수 설정
copy .env.example .env         # Windows
# cp .env.example .env          # macOS/Linux
# .env 파일을 열어 실제 API 키 입력

# 4. 앱 실행
streamlit run src/app/streamlit_app.py
```

## 필요한 API 키

`.env` 파일에 아래 키를 설정해야 합니다 (`.env.example` 참고):

| 변수명 | 발급처 |
|---|---|
| `ALPHA_VANTAGE_API_KEY` | https://www.alphavantage.co/support/#api-key |
| `OPENAI_API_KEY` | https://platform.openai.com/api-keys |
| `FRED_API_KEY` | https://fred.stlouisfed.org/docs/api/api_key.html |

## 프로젝트 구조

```
financial-ai-agent/
├── src/
│   ├── app/            # Streamlit 엔트리포인트
│   ├── config/         # 설정, 종목 검색
│   ├── data_loader/    # 시장/산업/종목 데이터 로딩
│   ├── llm/            # LLM 에이전트 (시장/산업/종목 분석, 리포트 생성)
│   ├── charts/         # 차트 생성
│   └── ui/             # 탭별 UI 렌더링
├── assets/             # 로고 등 이미지
├── notebooks/          # 실험용 노트북
├── requirements.txt
└── .env.example
```
