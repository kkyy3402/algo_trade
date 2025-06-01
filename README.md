# 알고리즘 트레이딩 봇 (algo_trade)

이 프로젝트는 Google의 AI, Jules의 도움을 받아 개발된 Python 기반 알고리즘 트레이딩 봇입니다.
볼린저 밴드와 Williams %R 지표를 트레이딩 시그널에 사용하며, 한국투자증권(KIS) API와 연동되도록 설계되었습니다. 이 봇은 FastAPI 백엔드와 Streamlit 기반 사용자 인터페이스를 특징으로 합니다.

[English Version](README_EN.md)

## 주요 기능

*   **트레이딩 전략**: 볼린저 밴드 및 Williams %R 기반.
*   **KIS API 연동**: 시장 데이터 조회, 계좌 정보 확인, 주문 실행 (사용자의 KIS API 키 필요).
*   **FastAPI 백엔드**: 다음을 위한 API 엔드포인트 제공:
    *   트레이딩 시그널을 위한 주식 스캔.
    *   거래 실행.
    *   포트폴리오 및 계좌 잔액 조회.
*   **Streamlit UI**: 다음을 위한 웹 기반 인터페이스:
    *   포트폴리오 모니터링.
    *   요청 시 주식 스캔.
    *   수동 거래 실행.
*   **스케줄링된 작업**: APScheduler를 사용한 사전 정의된 주식의 주기적 자동 스캔.
*   **확장 가능한 설계**: 손쉬운 수정 및 기능 추가를 위한 구조 (예: 새로운 트레이딩 전략).

## 프로젝트 구조

```
algo_trade/
├── backend/                  # 모든 백엔드 코드 포함 (FastAPI 앱 등)
│   ├── api/                  # API 엔드포인트 정의 (trading.py)
│   ├── core/                 # 핵심 로직 (KIS API, 지표, 설정)
│   ├── models/               # Pydantic 데이터 모델 (trade.py)
│   ├── services/             # 비즈니스 로직 서비스 (trading_service.py)
│   ├── scheduler/            # APScheduler 작업 (jobs.py)
│   ├── ui/                   # Streamlit UI 애플리케이션 (app_ui.py)
│   ├── main.py               # FastAPI 애플리케이션 진입점
│   ├── utils.py              # 유틸리티 함수
│   ├── requirements.txt      # 백엔드용 Python 의존성 파일
│   ├── requirements-dev.txt  # 개발용 의존성 파일
│   └── .env                  # API 키 및 기타 환경 변수용 (사용자가 .env.example 또는 지침에 따라 생성)
├── PLAN.txt                  # 개발 계획 및 진행 상황.
├── README.md                 # 이 파일 (한글).
└── README_EN.md              # 영문 README 파일.
```
*(참고: .env 파일은 사용자가 직접 생성해야 하며, 버전 관리에 포함되지 않아야 합니다.)*

## 설치 및 설정

1.  **리포지토리 복제:**
    ```bash
    git clone <repository_url>
    cd algo_trade
    ```

2.  **가상 환경 생성 (권장):**
    ```bash
    python -m venv venv
    source venv/bin/activate  # Windows: venv\Scripts\activate
    ```

3.  **의존성 설치:**
    `backend` 디렉토리로 이동하여 필요한 패키지를 설치합니다:
    ```bash
    cd backend
    pip install -r requirements.txt
    pip install -r requirements-dev.txt # pytest와 같은 개발 도구용
    ```
    *   **TA-Lib 참고**: `ta` 라이브러리가 사용됩니다. 만약 의존성(TA-Lib 자체 등) 관련 문제가 발생하면, 시스템에 TA-Lib C 라이브러리를 별도로 설치해야 할 수 있습니다. `ta` 라이브러리 문서 또는 [TA-Lib 공식 페이지](https://ta-lib.org/hdr_dw.html)에서 설치 지침을 참조하세요.

4.  **환경 변수 설정:**
    *   `backend` 디렉토리에 `.env`라는 이름의 파일을 생성합니다.
    *   이 파일에 한국투자증권 API 키와 계좌 정보를 추가합니다. 기존 `.env` 파일(플레이스홀더로 생성됨)을 템플릿으로 사용할 수 있습니다:
        ```env
        KIS_APP_KEY="YOUR_KIS_APP_KEY"
        KIS_APP_SECRET="YOUR_KIS_APP_SECRET"

        # KIS API 계좌번호 필요 함수용 (예: 잔고, 주문)
        # 실제 KIS 계좌 정보에서 정확한 값을 얻어 사용하세요. (모의투자 계좌 권장)
        KIS_ACCOUNT_CANO="YOUR_ACCOUNT_NUMBER_FIRST_8_DIGITS"
        KIS_ACCOUNT_ACNT_PRDT_CD="YOUR_ACCOUNT_PRODUCT_CODE_LAST_2_DIGITS"
        ```
    *   **중요**: 플레이스홀더 값을 실제 KIS API 자격 증명 및 계정 정보로 교체하십시오. 특히 주문 실행 테스트 시에는 **모의 투자 계좌**의 계좌번호를 사용해야 합니다.

## 애플리케이션 실행

애플리케이션은 FastAPI 백엔드와 Streamlit UI 두 가지 주요 부분으로 구성됩니다.

1.  **FastAPI 백엔드 시작:**
    *   `backend` 디렉토리로 이동합니다.
    *   Uvicorn 실행:
        ```bash
        uvicorn main:app --reload --host 0.0.0.0 --port 8000
        ```
    *   백엔드 API는 `http://localhost:8000`에서 접근할 수 있습니다.
    *   API 문서 (Swagger UI)는 `http://localhost:8000/docs`에서 확인할 수 있습니다.

2.  **Streamlit UI 시작:**
    *   **새 터미널** 창/탭을 엽니다.
    *   가상 환경을 활성화합니다 (아직 활성화되지 않은 경우).
    *   `backend` 디렉토리로 이동합니다 (프로젝트 루트 기준 `ui/app_ui.py`가 있는 위치, 또는 루트에서 Streamlit 실행 시 경로 조정).
    *   Streamlit 실행:
        ```bash
        streamlit run ui/app_ui.py
        ```
    *   Streamlit UI는 일반적으로 웹 브라우저에서 자동으로 열리며, 주소는 보통 `http://localhost:8501`입니다.

## 사용 방법

*   **백엔드 API**: Postman이나 curl과 같은 도구를 사용하여 API 엔드포인트와 직접 상호작용하거나, `/docs`에서 대화형 문서를 통해 확인할 수 있습니다.
*   **Streamlit UI**:
    *   **포트폴리오**: 현재 계좌 잔고 및 보유 종목을 확인합니다. "포트폴리오 새로고침"을 클릭하여 업데이트합니다.
    *   **주식 스캐너**: 쉼표로 구분된 종목 코드를 입력하여 구현된 전략에 따른 트레이딩 시그널을 받습니다.
    *   **수동 거래 실행**: 매수 또는 매도 주문을 실행합니다. 주문 유형 및 조건을 이해해야 합니다. **매우 신중하게 사용하고, 가급적 모의 투자 계좌로 테스트하십시오.**
*   **스케줄링된 작업**: 백엔드는 사전 정의된 주식 목록을 스캔하기 위해 스케줄링된 작업(기본: 매시간)을 실행합니다. 이러한 스캔 결과는 백엔드 로그에서 확인할 수 있습니다.

## 면책 조항

*   이것은 소프트웨어 개발 프로젝트이며 금융 자문이 아닙니다.
*   자동 트레이딩 시스템은 상당한 위험을 수반합니다.
*   **실제 돈으로 거래하기 전에 항상 가상/모의 투자 계좌로 철저히 테스트하십시오.**
*   개발자는 발생한 어떠한 금융 손실에 대해서도 책임을 지지 않습니다.
*   KIS API 사용이 해당 서비스 약관을 준수하는지 확인하십시오.

## 향후 개선 사항 (PLAN.txt 기반)

*   쉽게 교체 가능한 트레이딩 알고리즘을 위한 Strategy 패턴의 완전한 구현.
*   거래 내역, 시그널, 설정 저장을 위한 데이터베이스 연동.
*   더 정교한 오류 처리 및 알림 기능.
*   포괄적인 단위 및 통합 테스트.
*   UI 또는 설정 파일을 통한 스케줄러 빈도 및 주식 목록 구성 옵션.
