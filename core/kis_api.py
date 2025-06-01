import requests
import json
import os
from datetime import datetime, timedelta
import logging

# Assuming config.py is one level up if kis_api.py is in core
from .config import KIS_APP_KEY, KIS_APP_SECRET

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# --- KIS API Configuration ---
# These would be the actual base URLs for the KIS API
KIS_BASE_URL_REAL = "https://openapi.koreainvestment.com:9443"  # Real trading
KIS_BASE_URL_VIRTUAL = "https://openapivts.koreainvestment.com:29443" # Virtual trading

# For now, let's assume we can switch with a variable or a config setting
# It's highly recommended to start with the VIRTUAL (mock/paper trading) URL
CURRENT_KIS_BASE_URL = KIS_BASE_URL_VIRTUAL # Or KIS_BASE_URL_REAL

# Global session object for connection pooling
SESSION = requests.Session()
SESSION.headers.update({
    "content-type": "application/json",
    "appkey": KIS_APP_KEY,
    "appsecret": KIS_APP_SECRET,
    # Authorization token will be added after fetching it
})

ACCESS_TOKEN = None
TOKEN_EXPIRY_TIME = None

# --- Helper Functions ---
def _get_access_token():
    """
    Fetches a new access token from KIS API.
    This function needs to be implemented based on actual KIS API specs.
    Typically involves a POST request to a token endpoint with app_key and app_secret.
    """
    global ACCESS_TOKEN, TOKEN_EXPIRY_TIME

    # Example pseudo-code, actual implementation depends on KIS documentation
    token_url = f"{CURRENT_KIS_BASE_URL}/oauth2/tokenP"
    payload = {
        "grant_type": "client_credentials",
        "appkey": KIS_APP_KEY,
        "appsecret": KIS_APP_SECRET,
        # "scope": "oob" # if required by API
    }
    headers = {"content-type": "application/json"} # May vary

    try:
        response = SESSION.post(token_url, json=payload, headers=headers)
        response.raise_for_status() # Raise an exception for HTTP errors
        token_data = response.json()

        ACCESS_TOKEN = token_data.get("access_token")
        # KIS API typically returns expires_in (seconds)
        expires_in = token_data.get("expires_in", 3600) # Default to 1 hour
        TOKEN_EXPIRY_TIME = datetime.now() + timedelta(seconds=expires_in - 60) # Refresh a bit earlier

        SESSION.headers.update({"Authorization": f"Bearer {ACCESS_TOKEN}"})
        logging.info("Successfully fetched new KIS access token.")
        return True
    except requests.exceptions.RequestException as e:
        logging.error(f"Error fetching KIS access token: {e}")
        ACCESS_TOKEN = None
        TOKEN_EXPIRY_TIME = None
        return False

def _ensure_token_valid():
    """
    Ensures the access token is valid, fetching a new one if necessary.
    """
    global ACCESS_TOKEN, TOKEN_EXPIRY_TIME
    if not ACCESS_TOKEN or (TOKEN_EXPIRY_TIME and datetime.now() >= TOKEN_EXPIRY_TIME):
        logging.info("Access token expired or not available. Fetching new token.")
        if not _get_access_token():
            raise Exception("Failed to get or refresh KIS access token.")
    return True

def _make_api_request(method, endpoint_path, params=None, data=None, tr_id=None):
    """
    Makes a generic request to the KIS API, handling token and common headers.
    `tr_id` is often required by KIS for transaction identification.
    """
    _ensure_token_valid()

    url = f"{CURRENT_KIS_BASE_URL}{endpoint_path}"

    # Common headers for KIS requests
    request_headers = SESSION.headers.copy()
    if tr_id:
        request_headers["tr_id"] = tr_id
        # KIS also often requires a "custtype" (B for business, P for personal)
        request_headers["custtype"] = "P" # Assuming personal investor

    try:
        if method.upper() == "GET":
            response = SESSION.get(url, headers=request_headers, params=params)
        elif method.upper() == "POST":
            response = SESSION.post(url, headers=request_headers, params=params, json=data)
        else:
            raise ValueError(f"Unsupported HTTP method: {method}")

        response.raise_for_status()

        # KIS API responses often have 'rt_cd' (0 for success) and 'msg1'
        response_data = response.json()
        if response_data.get('rt_cd') != '0':
            error_message = response_data.get('msg1', 'Unknown API error')
            logging.error(f"KIS API Error ({endpoint_path}): {error_message} (Code: {response_data.get('rt_cd')})")
            # Consider raising a specific exception here
            raise Exception(f"KIS API Error: {error_message}")

        return response_data

    except requests.exceptions.HTTPError as http_err:
        logging.error(f"HTTP error occurred ({endpoint_path}): {http_err} - {response.text}")
        raise
    except requests.exceptions.RequestException as req_err:
        logging.error(f"Request error occurred ({endpoint_path}): {req_err}")
        raise
    except Exception as e:
        logging.error(f"An unexpected error occurred during API request ({endpoint_path}): {e}")
        raise

# --- API Functions ---

def get_stock_price(stock_code: str):
    """
    Fetches the current price of a given stock.
    Placeholder: Actual endpoint and params depend on KIS API.
    Example tr_id for current price: FHKST01010100 (Inquire Price)
    """
    endpoint = "/api/v1/quotations/inquire-price" # Example endpoint
    params = {
        "FID_COND_MRKT_DIV_CODE": "J", # J for Stock market
        "FID_INPUT_ISCD": stock_code,
    }
    # This tr_id is for "주식현재가 시세" (Stock current price)
    # For domestic stocks: "FHKST01010100"
    # For overseas stocks: "HHDFS00000300" (varies by market)
    # Needs to be confirmed from API docs.
    tr_id = "FHKST01010100"

    try:
        data = _make_api_request("GET", endpoint, params=params, tr_id=tr_id)
        # Process `data` to extract the price from `output` key in response
        # Example: price = data.get('output', {}).get('stck_prpr') # 'stck_prpr' is often 'stock present price'
        price_info = data.get('output', {})
        current_price = price_info.get('stck_prpr') # 현재가
        # logging.info(f"Price for {stock_code}: {current_price}")
        if current_price:
            return float(current_price)
        else:
            logging.warning(f"Could not extract price for {stock_code} from response: {price_info}")
            return None
    except Exception as e:
        logging.error(f"Error fetching price for {stock_code}: {e}")
        return None

def get_historical_stock_data(stock_code: str, start_date: str, end_date: str, period_code: str = "D"):
    """
    Fetches historical stock data (OHLCV) for a given stock and period.
    Placeholder: Actual endpoint and params depend on KIS API.
    `period_code`: D (Day), W (Week), M (Month)
    Example tr_id for daily chart: FHKST01010400 (Inquire Daily Chart Price)
                                 or FHKST03010100 (Inquire Period Price - domestic)
                                 or HHDFS76200200 (Inquire Period Price - overseas)
    """
    endpoint = "/api/v1/quotations/inquire-daily-price" # Example, might be different
    params = {
        "FID_COND_MRKT_DIV_CODE": "J",
        "FID_INPUT_ISCD": stock_code,
        "FID_INPUT_DATE_1": start_date.replace("-", ""), # YYYYMMDD
        "FID_INPUT_DATE_2": end_date.replace("-", ""),   # YYYYMMDD
        "FID_PERIOD_DIV_CODE": period_code, # D, W, M
        "FID_ORG_ADJ_PRC": "0" # 0 or 1 for adjusted price. Check API docs. Usually 1 for modified price.
    }
    # This tr_id is for "주식일봉데이터조회" (Stock daily candle data inquiry)
    # Domestic: FHKST01010400
    # Needs to be confirmed from API docs.
    tr_id = "FHKST01010400"

    try:
        data = _make_api_request("GET", endpoint, params=params, tr_id=tr_id)
        # Process `data` to extract OHLCV from `output1` (daily) or `output2` (periodical)
        # Example: ohlcv_list = data.get('output1', [])
        # Each item in ohlcv_list would be like:
        # {'stck_bsop_date': '20231020', 'stck_oprc': '70000', 'stck_hgpr': '71000', ...}
        ohlcv_data = data.get('output1', []) # output1 for daily price, output2 for weekly/monthly
        # Convert to a more usable format, e.g., list of dicts or pandas DataFrame
        formatted_data = []
        for item in ohlcv_data:
            formatted_data.append({
                "date": item.get("stck_bsop_date"),
                "open": float(item.get("stck_oprc", 0)),
                "high": float(item.get("stck_hgpr", 0)),
                "low": float(item.get("stck_lwpr", 0)),
                "close": float(item.get("stck_clpr", 0)),
                "volume": int(item.get("acml_vol", 0)) # 누적 거래량
            })
        # logging.info(f"Historical data for {stock_code} from {start_date} to {end_date}: {len(formatted_data)} records.")
        return formatted_data
    except Exception as e:
        logging.error(f"Error fetching historical data for {stock_code}: {e}")
        return []

def place_order(stock_code: str, order_type: str, quantity: int, price: float = 0, order_condition: str = "00"):
    """
    Places a buy or sell order.
    `order_type`: "01" (Sell), "02" (Buy) - KIS specific codes
    `price`: Required for limit orders. If 0 or not provided, might default to market order (depends on `order_condition`).
    `order_condition`: "00" (지정가 - Limit), "03" (시장가 - Market) - KIS specific codes
                       Other codes exist for IOC, FOK.
    Placeholder: Actual endpoint, tr_id, and params depend on KIS API.
    Example tr_id for domestic stock order: TTTC0802U (Buy), TTTC0801U (Sell)
    """
    _ensure_token_valid() # Make sure token is handled before any order

    # Determine tr_id based on order_type (Buy/Sell)
    # These are examples for domestic cash orders. Overseas/derivatives will have different tr_ids.
    if order_type == "02": # Buy
        tr_id = "TTTC0802U" # 현금 매수 주문 (Cash Buy Order)
    elif order_type == "01": # Sell
        tr_id = "TTTC0801U" # 현금 매도 주문 (Cash Sell Order)
    else:
        raise ValueError("Invalid order_type. Must be '01' (Sell) or '02' (Buy).")

    # Account number: First 8 digits are account prefix, last 2 are suffix.
    # This needs to be configured, e.g., from .env or a user setting.
    # KIS_ACCOUNT_NO_PREFIX = os.getenv("KIS_ACCOUNT_NO_PREFIX")
    # KIS_ACCOUNT_NO_SUFFIX = os.getenv("KIS_ACCOUNT_NO_SUFFIX")
    # if not KIS_ACCOUNT_NO_PREFIX or not KIS_ACCOUNT_NO_SUFFIX:
    #     raise ValueError("KIS Account number prefix and suffix not configured.")

    # For now, using placeholders. These MUST be correctly set.
    CANO = KIS_APP_KEY[:8] # Placeholder - this is NOT correct, use actual account number
    ACNT_PRDT_CD = KIS_APP_KEY[-2:] # Placeholder - this is NOT correct

    endpoint = "/api/v1/trading/order-cash" # Example endpoint for cash order
    payload = {
        "CANO": CANO, # 종합계좌번호 (Account number - first 8 digits)
        "ACNT_PRDT_CD": ACNT_PRDT_CD, # 계좌상품코드 (Account product code - last 2 digits)
        "PDNO": stock_code,             # 상품번호 (종목코드)
        "ORD_DVSN": order_condition,    # 주문구분 (00:지정가, 01:시장가 등 - KIS uses different codes, e.g. "00" for limit, "01" for market for some APIs, check docs)
        "ORD_QTY": str(quantity),       # 주문수량
        "ORD_UNPR": str(int(price)) if price > 0 and order_condition == "00" else "0", # 주문단가 (시장가면 0)
        # "ALGO_TRAD_CLS_CODE": "", # FOK, IOC 등 옵션 (선택)
    }

    try:
        response_data = _make_api_request("POST", endpoint, data=payload, tr_id=tr_id)
        # Process response_data. Successful orders usually return an order number.
        # Example: order_no = response_data.get('output', {}).get('ODNO')
        order_output = response_data.get('output', {})
        order_no = order_output.get('ODNO') # 주문번호
        # KIS also returns KRX_FWDG_ORD_ORGNO, ORD_TMD (주문시각)
        logging.info(f"Order placed for {stock_code}. Type: {order_type}, Qty: {quantity}, Price: {price}. Order No: {order_no}")
        return {"success": True, "order_id": order_no, "details": order_output}
    except Exception as e:
        logging.error(f"Error placing order for {stock_code}: {e}")
        return {"success": False, "error": str(e)}

def get_account_balance():
    """
    Fetches the current account balance and holdings.
    Placeholder: Actual endpoint, tr_id, and params depend on KIS API.
    Example tr_id for domestic balance: TTTC8434R (주식잔고조회)
                      or CTOS0002R (계좌 예수금/증거금 현황 조회)
    """
    # This tr_id is for "주식잔고합산조회" (Consolidated Stock Balance Inquiry)
    # For domestic stocks: "TTTC8434R"
    # For overseas stocks: "JTTT3012R" or "OD quantité" (varies by market)
    # Needs to be confirmed from API docs.
    tr_id_balance = "TTTC8434R" # Example, for domestic stock balance

    # CANO = KIS_APP_KEY[:8] # Placeholder
    # ACNT_PRDT_CD = KIS_APP_KEY[-2:] # Placeholder
    CANO = os.getenv("KIS_ACCOUNT_CANO", "YOUR_CANO") # Actual account number
    ACNT_PRDT_CD = os.getenv("KIS_ACCOUNT_ACNT_PRDT_CD", "01") # Actual account product code

    endpoint = "/api/v1/trading/inquire-balance" # Example endpoint
    params = {
        "CANO": CANO,
        "ACNT_PRDT_CD": ACNT_PRDT_CD,
        "AFHR_FLPR_YN": "N", # 시간외단일가여부 (N: No, Y: Yes)
        "OFL_YN": "", # 공란
        "INQR_DVSN": "01", # 조회구분 (01: 대출일별, 02: 종목별) - might need to be "02" for detailed holdings
        "UNPR_DVSN": "01", # 단가구분 (01: 평균단가, 02: BEP단가)
        "FUND_STTL_ICLD_YN": "N", # 펀드결제분포함여부
        "FNCG_AMT_AUTO_RDPT_YN": "N", # 융자금액자동상환여부
        "PRCS_DVSN": "00", # 처리구분 (00: 전일매매포함)
        "CTX_AREA_FK100": "", # 연속조회검색조건100
        "CTX_AREA_NK100": ""  # 연속조회키100
    }

    try:
        data = _make_api_request("GET", endpoint, params=params, tr_id=tr_id_balance)
        # Process data, which might be split into `output1` (list of holdings) and `output2` (summary)
        # Example: holdings = data.get('output1', [])
        #          summary = data.get('output2', {})
        #          cash_balance = summary.get('dnca_tot_amt') # 예수금 총금액

        holdings_list = data.get('output1', [])
        summary_info = data.get('output2', []) # output2 is also often a list, even if one item

        parsed_holdings = []
        for item in holdings_list:
            parsed_holdings.append({
                "stock_code": item.get("pdno"),
                "stock_name": item.get("prdt_name"),
                "quantity": int(item.get("hldg_qty",0)),
                "average_purchase_price": float(item.get("pchs_avg_pric",0)),
                "current_price": float(item.get("prpr",0)),
                "eval_amount": float(item.get("evlu_amt",0)),
                "profit_loss_amount": float(item.get("evlu_pfls_amt",0)),
                "profit_loss_ratio": float(item.get("evlu_pfls_rt",0)),
            })

        cash_details = {}
        if summary_info and isinstance(summary_info, list) and len(summary_info) > 0:
             # 예수금총금액, D+2예수금 등
            cash_details = {
                "total_cash_balance": float(summary_info[0].get("dnca_tot_amt", 0)), # 예수금총금액
                "eval_amount_total": float(summary_info[0].get("tot_evlu_amt", 0)), # 총평가금액
                "net_asset_value": float(summary_info[0].get("nass_amt",0)), # 순자산금액
                # Add more fields as needed from output2
            }

        # logging.info(f"Account balance fetched. Holdings: {len(parsed_holdings)} items. Cash: {cash_details.get('total_cash_balance')}")
        return {"holdings": parsed_holdings, "summary": cash_details}
    except Exception as e:
        logging.error(f"Error fetching account balance: {e}")
        return {"holdings": [], "summary": {}, "error": str(e)}

# --- Initialization ---
# Attempt to get a token when the module is loaded, or on first API call.
# It might be better to do this lazily (on first actual API function call)
# _get_access_token() # Or call this within each public function, guarded by _ensure_token_valid()

if __name__ == "__main__":
    # This section is for testing the API functions directly.
    # Requires .env file with KIS_APP_KEY and KIS_APP_SECRET
    # and KIS_ACCOUNT_CANO, KIS_ACCOUNT_ACNT_PRDT_CD for balance/order

    # IMPORTANT: Ensure you have your .env file correctly set up in the parent directory
    # or wherever core.config expects it.
    # Example:
    # KIS_APP_KEY="your_app_key"
    # KIS_APP_SECRET="your_app_secret"
    # KIS_ACCOUNT_CANO="your_account_number_first_8_digits"
    # KIS_ACCOUNT_ACNT_PRDT_CD="your_account_number_last_2_digits_product_code"

    if not KIS_APP_KEY or not KIS_APP_SECRET:
        print("KIS_APP_KEY or KIS_APP_SECRET not found in environment. Please set them in .env file.")
    else:
        print(f"KIS_APP_KEY: {KIS_APP_KEY[:5]}...") # Print partial key for confirmation

        # Test token fetching (implicitly called by other functions)
        # if _ensure_token_valid():
        #    print(f"Access Token obtained: {ACCESS_TOKEN[:10]}...")
        # else:
        #    print("Failed to obtain access token.")
        #    exit()

        # Test fetching stock price (e.g., Samsung Electronics: 005930)
        # stock_code_to_test = "005930"
        # print(f"\nFetching current price for {stock_code_to_test}...")
        # price = get_stock_price(stock_code_to_test)
        # if price:
        #     print(f"Current price of {stock_code_to_test}: {price}")
        # else:
        #     print(f"Could not fetch price for {stock_code_to_test}.")

        # Test fetching historical data
        # print(f"\nFetching historical data for {stock_code_to_test}...")
        # historical_data = get_historical_stock_data(stock_code_to_test, "20231001", "20231020", "D")
        # if historical_data:
        #     print(f"Fetched {len(historical_data)} days of data for {stock_code_to_test}.")
        #     # print("Last data point:", historical_data[-1] if historical_data else "N/A")
        # else:
        #     print(f"Could not fetch historical data for {stock_code_to_test}.")

        # Test account balance (Requires account numbers in .env)
        # print("\nFetching account balance...")
        # balance_info = get_account_balance()
        # if "error" not in balance_info:
        #     print("Account Balance Summary:", balance_info.get("summary"))
        #     print("Holdings:", balance_info.get("holdings"))
        # else:
        #     print("Could not fetch account balance:", balance_info.get("error"))

        # Test placing an order (USE WITH EXTREME CAUTION, PREFERABLY ON VIRTUAL ACCOUNT)
        # print("\nAttempting to place a **TEST** order (ensure VIRTUAL trading environment)...")
        # Note: For real orders, ensure all parameters (stock_code, quantity, price, order_condition, account details) are correct.
        # This is a hypothetical buy order for 1 share of stock "005930" at market price.
        # Ensure your KIS_ACCOUNT_CANO and KIS_ACCOUNT_ACNT_PRDT_CD are set in .env
        # test_order_stock = "005930" # Samsung Electronics
        # test_order_result = place_order(
        #     stock_code=test_order_stock,
        #     order_type="02",  # Buy
        #     quantity=1,
        #     price=0,          # Market order price is 0
        #     order_condition="03" # Market order ("시장가") - KIS code may vary, check "주문구분"
        # )
        # print("Test Order Result:", test_order_result)
        pass # End of main test block

    print("Placeholder core/kis_api.py created with function structures.")
    print("Actual implementation requires KIS API documentation for endpoints, request/response formats, and auth.")
    print("Ensure to use the VIRTUAL TRADING URL (openapivts.koreainvestment.com) for development and testing.")
    print("The file includes examples for token fetching, getting price, historical data, placing orders, and checking balance.")
    print("Logging is also included.")
    print("A __main__ block is added for basic testing of the functions (currently commented out).")
