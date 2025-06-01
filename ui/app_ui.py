import streamlit as st
import requests
import pandas as pd
from datetime import datetime

# --- 설정 ---
FASTAPI_BASE_URL = "http://localhost:8000/api" # FastAPI가 포트 8000에서 실행된다고 가정

# --- 백엔드 연동 헬퍼 함수 ---
def get_portfolio():
    try:
        response = requests.get(f"{FASTAPI_BASE_URL}/portfolio")
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        st.error(f"포트폴리오 조회 오류: {e}")
        return None

def scan_stocks(stock_codes: list):
    try:
        payload = {"stock_codes": stock_codes}
        response = requests.post(f"{FASTAPI_BASE_URL}/scan_stocks", json=payload)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        st.error(f"주식 스캔 오류: {e}")
        return None

def execute_trade(stock_symbol: str, order_type: str, quantity: int, price: float = 0, order_condition: str = "00"):
    # 필요한 경우 사용자 친화적 용어를 KIS 코드로 매핑하거나 코드 직접 사용 기대
    # KIS용: order_type "01" (매도), "02" (매수)
    #          order_condition "00" (지정가), "03" (시장가)
    payload = {
        "stock_symbol": stock_symbol,
        "order_type": order_type,
        "quantity": quantity,
        "price": price,
        "order_condition": order_condition
    }
    try:
        response = requests.post(f"{FASTAPI_BASE_URL}/execute_trade", json=payload)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        st.error(f"거래 실행 오류: {e}")
        return None

# --- Streamlit UI 레이아웃 ---
st.set_page_config(layout="wide", page_title="트레이딩 봇 UI")
st.title("📈 알고리즘 트레이딩 봇 인터페이스")

# --- 포트폴리오 표시 ---
st.header("💼 포트폴리오 개요")
if st.button("포트폴리오 새로고침"):
    st.session_state.portfolio_data = get_portfolio()

portfolio_data = st.session_state.get('portfolio_data')

if portfolio_data:
    if portfolio_data.get("summary"):
        summary = portfolio_data["summary"]
        col1, col2, col3 = st.columns(3)
        col1.metric("총 보유 현금", f"₩{summary.get('total_cash_balance', 0):,.0f}" if summary.get('total_cash_balance') is not None else "해당 없음")
        col2.metric("총 평가 금액 (자산)", f"₩{summary.get('eval_amount_total', 0):,.0f}" if summary.get('eval_amount_total') is not None else "해당 없음")
        col3.metric("순자산 가치", f"₩{summary.get('net_asset_value', 0):,.0f}" if summary.get('net_asset_value') is not None else "해당 없음")

    if portfolio_data.get("holdings"):
        holdings_df = pd.DataFrame(portfolio_data["holdings"])
        st.subheader("현재 보유 종목")
        if not holdings_df.empty:
            # 더 나은 표시를 위해 열 선택 및 이름 변경
            display_cols = {
                "stock_code": "종목코드",
                "stock_name": "종목명",
                "quantity": "수량",
                "average_purchase_price": "평균 매입 단가",
                "current_price": "현재가",
                "eval_amount": "평가 금액",
                "profit_loss_amount": "손익 금액",
                "profit_loss_ratio": "손익률 (%)"
            }
            holdings_df_display = holdings_df[list(display_cols.keys())].rename(columns=display_cols)
            st.dataframe(holdings_df_display, use_container_width=True)
        else:
            st.write("표시할 보유 종목이 없습니다.")
    else:
        st.write("보유 종목 데이터가 없습니다.")
else:
    st.info("'포트폴리오 새로고침'을 클릭하여 현재 포트폴리오를 로드하세요.")


# --- 주식 스캐너 섹션 ---
st.header("🔍 주식 스캐너")
stock_input_str = st.text_input("스캔할 종목 코드를 입력하세요 (쉼표로 구분, 예: 005930,035720):", "005930,035720")

if st.button("주식 스캔"):
    if stock_input_str:
        stock_codes_to_scan = [code.strip() for code in stock_input_str.split(",") if code.strip()]
        if stock_codes_to_scan:
            with st.spinner("주식 스캔 중... 잠시 기다려주세요."):
                scan_results = scan_stocks(stock_codes_to_scan)

            st.session_state.scan_results = scan_results # 세션 상태에 저장
        else:
            st.warning("유효한 종목 코드를 입력하세요.")
    else:
        st.warning("스캔할 종목 코드를 입력하세요.")

scan_results_data = st.session_state.get('scan_results')
if scan_results_data:
    st.subheader("스캔 결과")
    results_df = pd.DataFrame(scan_results_data)
    if not results_df.empty:
        # 스캔 결과 표시 사용자 정의
        # 지표 값이 존재하면 명확성을 위해 별도 열로 추출
        if 'indicators' in results_df.columns and results_df['indicators'].notna().any():
            try:
                indicators_df = results_df['indicators'].apply(pd.Series)
                results_df = pd.concat([results_df.drop(['indicators'], axis=1), indicators_df], axis=1)
            except Exception as e:
                st.warning(f"일부 지표를 파싱할 수 없습니다: {e}")


        # 표시할 열 재정렬 및 선택
        display_cols_scan = [
            "stock_code", "signal", "reason", "price_at_signal", "current_market_price",
            "bollinger_lower", "bollinger_middle", "bollinger_upper", "williams_r", "timestamp"
        ]
        # 누락된 열(예: 지표)이 있을 경우 기존 열만 필터링
        existing_display_cols = [col for col in display_cols_scan if col in results_df.columns]

        st.dataframe(results_df[existing_display_cols], height=300, use_container_width=True)

        # 결과를 지우거나 유지하는 방법 제공
        if st.button("스캔 결과 지우기"):
            st.session_state.scan_results = None
            st.rerun() # 표시를 지우기 위해 강제 재실행
    else:
        st.write("표시할 스캔 결과가 없거나 오류가 발생했습니다.")


# --- 수동 거래 실행 섹션 ---
st.header("🛒 수동 거래 실행")
with st.form("trade_form"):
    col_trade1, col_trade2, col_trade3, col_trade4 = st.columns([2,1,1,1])
    trade_stock_symbol = col_trade1.text_input("종목 코드 (예: 005930)", "005930")

    # 사용자 친화적 선택, execute_trade 또는 API에서 KIS 코드로 매핑
    trade_order_type_display = col_trade2.selectbox("주문 유형", ["매수", "매도"], index=0)

    trade_quantity = col_trade3.number_input("수량", min_value=1, value=1)

    # KIS 주문 조건 코드: "00" (지정가), "03" (시장가)
    trade_order_condition_display = col_trade4.selectbox("주문 조건", ["지정가", "시장가"], index=0)

    trade_price = 0.0
    if trade_order_condition_display == "지정가": # "Limit (지정가)" 에서 "지정가" 로 변경
        trade_price = st.number_input("가격 (지정가 주문용)", min_value=0.0, value=0.0, format="%.0f") # format="%.2f" 에서 "%.0f"로 변경 (원화 가정)

    submitted = st.form_submit_button("주문 실행")

if submitted:
    # 표시 이름을 KIS API 코드로 매핑
    kis_order_type = "02" if trade_order_type_display == "매수" else "01"
    kis_order_condition = "00" if trade_order_condition_display == "지정가" else "03" # KIS 예시

    if not trade_stock_symbol:
        st.error("종목 코드는 필수입니다.")
    else:
        with st.spinner("주문 실행 중..."):
            trade_result = execute_trade(
                stock_symbol=trade_stock_symbol,
                order_type=kis_order_type,
                quantity=trade_quantity,
                price=trade_price if kis_order_condition == "00" else 0, # 시장가 주문 시 가격은 0
                order_condition=kis_order_condition
            )
        if trade_result:
            if trade_result.get("status") == "FAILED":
                st.error(f"거래 실패: {trade_result.get('message', '알 수 없는 오류.')}")
                if trade_result.get('details'):
                    st.json(trade_result.get('details'))
            else:
                st.success(f"주문 제출됨: {trade_result.get('message', '성공!')}")
                st.json(trade_result) # 전체 응답 표시
            # 선택적으로 거래 후 포트폴리오 새로고침
            st.session_state.portfolio_data = get_portfolio()
            st.rerun()


st.sidebar.header("정보")
st.sidebar.info(
    "이것은 알고리즘 트레이딩 봇을 위한 UI입니다. "
    "FastAPI 백엔드와 상호작용하여 데이터를 가져오고, 주식을 스캔하며, 거래를 실행합니다."
)
st.sidebar.warning(
    "**면책 조항:** 트레이딩에는 위험이 따릅니다. 이것은 데모 애플리케이션입니다. "
    "테스트 시에는 반드시 가상/모의 트레이딩 계좌를 사용하십시오. "
    "실거래 전에 모든 KIS API 코드와 파라미터를 확인하십시오."
)

# 이 Streamlit 앱을 실행하려면:
# 1. FastAPI 백엔드(main.py)가 실행 중인지 확인합니다.
# 2. 프로젝트 루트에서 터미널을 엽니다.
# 3. 실행: streamlit run ui/app_ui.py
