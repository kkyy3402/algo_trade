import streamlit as st
import requests
import pandas as pd
from datetime import datetime

# --- Configuration ---
FASTAPI_BASE_URL = "http://localhost:8000/api" # Assuming FastAPI runs on port 8000

# --- Helper Functions to Interact with Backend ---
def get_portfolio():
    try:
        response = requests.get(f"{FASTAPI_BASE_URL}/portfolio")
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        st.error(f"Error fetching portfolio: {e}")
        return None

def scan_stocks(stock_codes: list):
    try:
        payload = {"stock_codes": stock_codes}
        response = requests.post(f"{FASTAPI_BASE_URL}/scan_stocks", json=payload)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        st.error(f"Error scanning stocks: {e}")
        return None

def execute_trade(stock_symbol: str, order_type: str, quantity: int, price: float = 0, order_condition: str = "00"):
    # Map user-friendly terms to KIS codes if necessary, or expect codes directly
    # For KIS: order_type "01" (Sell), "02" (Buy)
    #          order_condition "00" (Limit), "03" (Market)
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
        st.error(f"Error executing trade: {e}")
        return None

# --- Streamlit UI Layout ---
st.set_page_config(layout="wide", page_title="Trading Bot UI")
st.title("📈 Algorithmic Trading Bot Interface")

# --- Portfolio Display ---
st.header("💼 Portfolio Overview")
if st.button("Refresh Portfolio"):
    st.session_state.portfolio_data = get_portfolio()

portfolio_data = st.session_state.get('portfolio_data')

if portfolio_data:
    if portfolio_data.get("summary"):
        summary = portfolio_data["summary"]
        col1, col2, col3 = st.columns(3)
        col1.metric("Total Cash Balance", f"₩{summary.get('total_cash_balance', 0):,.0f}" if summary.get('total_cash_balance') is not None else "N/A")
        col2.metric("Total Evaluated Amount (Assets)", f"₩{summary.get('eval_amount_total', 0):,.0f}" if summary.get('eval_amount_total') is not None else "N/A")
        col3.metric("Net Asset Value", f"₩{summary.get('net_asset_value', 0):,.0f}" if summary.get('net_asset_value') is not None else "N/A")

    if portfolio_data.get("holdings"):
        holdings_df = pd.DataFrame(portfolio_data["holdings"])
        st.subheader("Current Holdings")
        if not holdings_df.empty:
            # Select and rename columns for better display
            display_cols = {
                "stock_code": "Symbol",
                "stock_name": "Name",
                "quantity": "Quantity",
                "average_purchase_price": "Avg. Purchase Price",
                "current_price": "Current Price",
                "eval_amount": "Evaluation Amount",
                "profit_loss_amount": "P/L Amount",
                "profit_loss_ratio": "P/L Ratio (%)"
            }
            holdings_df_display = holdings_df[list(display_cols.keys())].rename(columns=display_cols)
            st.dataframe(holdings_df_display, use_container_width=True)
        else:
            st.write("No holdings to display.")
    else:
        st.write("No holdings data available.")
else:
    st.info("Click 'Refresh Portfolio' to load your current portfolio.")


# --- Stock Scanning Section ---
st.header("🔍 Stock Scanner")
stock_input_str = st.text_input("Enter stock codes to scan (comma-separated, e.g., 005930,035720):", "005930,035720")

if st.button("Scan Stocks"):
    if stock_input_str:
        stock_codes_to_scan = [code.strip() for code in stock_input_str.split(",") if code.strip()]
        if stock_codes_to_scan:
            with st.spinner("Scanning stocks... This may take a moment."):
                scan_results = scan_stocks(stock_codes_to_scan)

            st.session_state.scan_results = scan_results # Store in session state
        else:
            st.warning("Please enter valid stock codes.")
    else:
        st.warning("Please enter stock codes to scan.")

scan_results_data = st.session_state.get('scan_results')
if scan_results_data:
    st.subheader("Scan Results")
    results_df = pd.DataFrame(scan_results_data)
    if not results_df.empty:
        # Customize display of scan results
        # Extract indicator values into separate columns for clarity if they exist
        if 'indicators' in results_df.columns and results_df['indicators'].notna().any():
            try:
                indicators_df = results_df['indicators'].apply(pd.Series)
                results_df = pd.concat([results_df.drop(['indicators'], axis=1), indicators_df], axis=1)
            except Exception as e:
                st.warning(f"Could not parse all indicators: {e}")


        # Reorder and select columns for display
        display_cols_scan = [
            "stock_code", "signal", "reason", "price_at_signal", "current_market_price",
            "bollinger_lower", "bollinger_middle", "bollinger_upper", "williams_r", "timestamp"
        ]
        # Filter for existing columns only, in case some are missing (e.g. indicators)
        existing_display_cols = [col for col in display_cols_scan if col in results_df.columns]

        st.dataframe(results_df[existing_display_cols], height=300, use_container_width=True)

        # Provide a way to clear results or they persist
        if st.button("Clear Scan Results"):
            st.session_state.scan_results = None
            st.rerun() # Force rerun to clear the display
    else:
        st.write("No scan results to display or an error occurred.")


# --- Manual Trade Execution Section ---
st.header("🛒 Manual Trade Execution")
with st.form("trade_form"):
    col_trade1, col_trade2, col_trade3, col_trade4 = st.columns([2,1,1,1])
    trade_stock_symbol = col_trade1.text_input("Stock Symbol (e.g., 005930)", "005930")

    # User-friendly selection, mapped to KIS codes in execute_trade or API
    trade_order_type_display = col_trade2.selectbox("Order Type", ["BUY", "SELL"], index=0)

    trade_quantity = col_trade3.number_input("Quantity", min_value=1, value=1)

    # KIS order condition codes: "00" (지정가 Limit), "03" (시장가 Market)
    trade_order_condition_display = col_trade4.selectbox("Order Condition", ["Limit (지정가)", "Market (시장가)"], index=0)

    trade_price = 0.0
    if trade_order_condition_display == "Limit (지정가)":
        trade_price = st.number_input("Price (for Limit Order)", min_value=0.0, value=0.0, format="%.2f")

    submitted = st.form_submit_button("Execute Trade")

if submitted:
    # Map display names to KIS API codes
    kis_order_type = "02" if trade_order_type_display == "BUY" else "01"
    kis_order_condition = "00" if trade_order_condition_display == "Limit (지정가)" else "03" # Example for KIS

    if not trade_stock_symbol:
        st.error("Stock symbol is required.")
    else:
        with st.spinner("Executing trade..."):
            trade_result = execute_trade(
                stock_symbol=trade_stock_symbol,
                order_type=kis_order_type,
                quantity=trade_quantity,
                price=trade_price if kis_order_condition == "00" else 0, # Price is 0 for market order
                order_condition=kis_order_condition
            )
        if trade_result:
            if trade_result.get("status") == "FAILED":
                st.error(f"Trade Failed: {trade_result.get('message', 'Unknown error')}")
                if trade_result.get('details'):
                    st.json(trade_result.get('details'))
            else:
                st.success(f"Trade Submitted: {trade_result.get('message', 'Success!')}")
                st.json(trade_result) # Display full response
            # Optionally, refresh portfolio after a trade
            st.session_state.portfolio_data = get_portfolio()
            st.rerun()


st.sidebar.header("About")
st.sidebar.info(
    "This is a UI for the Algorithmic Trading Bot. "
    "It interacts with a FastAPI backend to fetch data, scan stocks, and execute trades."
)
st.sidebar.warning(
    "**Disclaimer:** Trading involves risks. This is a demo application. "
    "Ensure you are using a virtual/paper trading account for any tests. "
    "Verify all KIS API codes and parameters before live trading."
)

# To run this Streamlit app:
# 1. Ensure the FastAPI backend (main.py) is running.
# 2. Open your terminal in the project root.
# 3. Run: streamlit run ui/app_ui.py
