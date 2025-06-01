import requests
import json
import os
from datetime import datetime, timedelta
import logging

# config.py가 kis_api.py와 같은 core 디렉토리에 있거나 상위 경로에 있다고 가정합니다.
from .config import KIS_APP_KEY, KIS_APP_SECRET

# 로깅 설정
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# --- KIS API 설정 ---
# KIS API의 실제 기본 URL이어야 합니다.
KIS_BASE_URL_REAL = "https://openapi.koreainvestment.com:9443"  # 실거래
KIS_BASE_URL_VIRTUAL = "https://openapivts.koreainvestment.com:29443" # 모의 투자

# 지금은 변수나 설정으로 전환 가능하다고 가정합니다.
# 가상(모의/페이퍼 트레이딩) URL로 시작하는 것을 강력히 권장합니다.
CURRENT_KIS_BASE_URL = KIS_BASE_URL_VIRTUAL # 또는 KIS_BASE_URL_REAL

# 커넥션 풀링을 위한 전역 세션 객체
SESSION = requests.Session()
SESSION.headers.update({
    "content-type": "application/json",
    "appkey": KIS_APP_KEY,
    "appsecret": KIS_APP_SECRET,
    # 인증 토큰은 가져온 후 추가될 예정입니다.
})

ACCESS_TOKEN = None
TOKEN_EXPIRY_TIME = None

# --- 헬퍼 함수 ---
def _get_access_token():
    """
    KIS API에서 새 액세스 토큰을 가져옵니다.
    이 함수는 실제 KIS API 명세에 따라 구현되어야 합니다.
    일반적으로 app_key와 app_secret을 사용하여 토큰 엔드포인트에 POST 요청을 보냅니다.
    """
    global ACCESS_TOKEN, TOKEN_EXPIRY_TIME

    # 예제 의사 코드, 실제 구현은 KIS 문서에 따라 다릅니다.
    token_url = f"{CURRENT_KIS_BASE_URL}/oauth2/tokenP"
    payload = {
        "grant_type": "client_credentials",
        "appkey": KIS_APP_KEY,
        "appsecret": KIS_APP_SECRET,
        # "scope": "oob" # API에서 요구하는 경우
    }
    headers = {"content-type": "application/json"} # 다를 수 있습니다.

    try:
        response = SESSION.post(token_url, json=payload, headers=headers)
        response.raise_for_status() # HTTP 오류에 대해 예외 발생
        token_data = response.json()

        ACCESS_TOKEN = token_data.get("access_token")
        # KIS API는 일반적으로 expires_in (초)을 반환합니다.
        expires_in = token_data.get("expires_in", 3600) # 기본값 1시간
        TOKEN_EXPIRY_TIME = datetime.now() + timedelta(seconds=expires_in - 60) # 조금 일찍 새로고침

        SESSION.headers.update({"Authorization": f"Bearer {ACCESS_TOKEN}"})
        logging.info("KIS 액세스 토큰을 성공적으로 가져왔습니다.")
        return True
    except requests.exceptions.RequestException as e:
        logging.error(f"KIS 액세스 토큰 조회 중 오류 발생: {e}")
        ACCESS_TOKEN = None
        TOKEN_EXPIRY_TIME = None
        return False

def _ensure_token_valid():
    """
    액세스 토큰이 유효한지 확인하고, 필요한 경우 새로 가져옵니다.
    """
    global ACCESS_TOKEN, TOKEN_EXPIRY_TIME
    if not ACCESS_TOKEN or (TOKEN_EXPIRY_TIME and datetime.now() >= TOKEN_EXPIRY_TIME):
        logging.info("액세스 토큰이 만료되었거나 없습니다. 새 토큰을 가져옵니다.")
        if not _get_access_token():
            raise Exception("KIS 액세스 토큰을 가져오거나 갱신하는 데 실패했습니다.")
    return True

def _make_api_request(method, endpoint_path, params=None, data=None, tr_id=None):
    """
    토큰 및 공통 헤더를 처리하며 KIS API에 일반 요청을 보냅니다.
    `tr_id`는 종종 KIS에서 거래 식별을 위해 필요합니다.
    """
    _ensure_token_valid()

    url = f"{CURRENT_KIS_BASE_URL}{endpoint_path}"

    # KIS 요청 공통 헤더
    request_headers = SESSION.headers.copy()
    if tr_id:
        request_headers["tr_id"] = tr_id
        # KIS는 종종 "custtype"(B: 법인, P: 개인)을 요구합니다.
        request_headers["custtype"] = "P" # 개인 투자자로 가정

    try:
        if method.upper() == "GET":
            response = SESSION.get(url, headers=request_headers, params=params)
        elif method.upper() == "POST":
            response = SESSION.post(url, headers=request_headers, params=params, json=data)
        else:
            raise ValueError(f"지원하지 않는 HTTP 메소드: {method}")

        response.raise_for_status()

        # KIS API 응답에는 종종 'rt_cd'(0: 성공)와 'msg1'이 있습니다.
        response_data = response.json()
        if response_data.get('rt_cd') != '0':
            error_message = response_data.get('msg1', '알 수 없는 API 오류')
            logging.error(f"KIS API 오류 ({endpoint_path}): {error_message} (코드: {response_data.get('rt_cd')})")
            # 여기서 특정 예외 발생 고려
            raise Exception(f"KIS API 오류: {error_message}")

        return response_data

    except requests.exceptions.HTTPError as http_err:
        logging.error(f"HTTP 오류 발생 ({endpoint_path}): {http_err} - {response.text}")
        raise
    except requests.exceptions.RequestException as req_err:
        logging.error(f"요청 오류 발생 ({endpoint_path}): {req_err}")
        raise
    except Exception as e:
        logging.error(f"API 요청 중 예기치 않은 오류 발생 ({endpoint_path}): {e}")
        raise

# --- API 함수 ---

def get_stock_price(stock_code: str):
    """
    주어진 주식의 현재가를 가져옵니다.
    플레이스홀더: 실제 엔드포인트와 파라미터는 KIS API에 따라 다릅니다.
    현재가 조회 예시 tr_id: FHKST01010100 (시세 조회)
    """
    endpoint = "/api/v1/quotations/inquire-price" # 예시 엔드포인트
    params = {
        "FID_COND_MRKT_DIV_CODE": "J", # J: 주식 시장
        "FID_INPUT_ISCD": stock_code,
    }
    # 이 tr_id는 "주식현재가 시세"용입니다.
    # 국내 주식용: "FHKST01010100"
    # 해외 주식용: "HHDFS00000300" (시장에 따라 다름)
    # API 문서에서 확인 필요.
    tr_id = "FHKST01010100"

    try:
        data = _make_api_request("GET", endpoint, params=params, tr_id=tr_id)
        # 응답의 `output` 키에서 가격을 추출하기 위해 `data` 처리
        # 예: price = data.get('output', {}).get('stck_prpr') # 'stck_prpr'은 종종 '현재 주가'를 의미함.
        price_info = data.get('output', {})
        current_price = price_info.get('stck_prpr') # 현재가
        # logging.info(f"{stock_code} 가격: {current_price}")
        if current_price:
            return float(current_price)
        else:
            logging.warning(f"응답에서 {stock_code}의 가격을 추출할 수 없습니다: {price_info}")
            return None
    except Exception as e:
        logging.error(f"{stock_code} 가격 조회 중 오류 발생: {e}")
        return None

def get_historical_stock_data(stock_code: str, start_date: str, end_date: str, period_code: str = "D"):
    """
    주어진 주식 및 기간에 대한 과거 주가 데이터(OHLCV)를 가져옵니다.
    플레이스홀더: 실제 엔드포인트와 파라미터는 KIS API에 따라 다릅니다.
    `period_code`: D (일), W (주), M (월)
    일별 차트 예시 tr_id: FHKST01010400 (일별 차트 가격 조회)
                                 또는 FHKST03010100 (기간별 가격 조회 - 국내)
                                 또는 HHDFS76200200 (기간별 가격 조회 - 해외)
    """
    endpoint = "/api/v1/quotations/inquire-daily-price" # 예시, 다를 수 있음
    params = {
        "FID_COND_MRKT_DIV_CODE": "J",
        "FID_INPUT_ISCD": stock_code,
        "FID_INPUT_DATE_1": start_date.replace("-", ""), # YYYYMMDD
        "FID_INPUT_DATE_2": end_date.replace("-", ""),   # YYYYMMDD
        "FID_PERIOD_DIV_CODE": period_code, # D, W, M
        "FID_ORG_ADJ_PRC": "0" # 0 또는 1 (수정 주가). API 문서 확인. 보통 1이 수정 주가.
    }
    # 이 tr_id는 "주식일봉데이터조회"용입니다.
    # 국내: FHKST01010400
    # API 문서에서 확인 필요.
    tr_id = "FHKST01010400"

    try:
        data = _make_api_request("GET", endpoint, params=params, tr_id=tr_id)
        # `output1`(일별) 또는 `output2`(기간별)에서 OHLCV를 추출하기 위해 `data` 처리
        # 예: ohlcv_list = data.get('output1', [])
        # ohlcv_list의 각 항목은 다음과 같음:
        # {'stck_bsop_date': '20231020', 'stck_oprc': '70000', 'stck_hgpr': '71000', ...}
        ohlcv_data = data.get('output1', []) # output1: 일별 가격, output2: 주별/월별 가격
        # 더 사용하기 쉬운 형식으로 변환 (예: 딕셔너리 리스트 또는 Pandas DataFrame)
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
        # logging.info(f"{stock_code}의 {start_date}부터 {end_date}까지 과거 데이터: {len(formatted_data)}건.")
        return formatted_data
    except Exception as e:
        logging.error(f"{stock_code} 과거 데이터 조회 중 오류 발생: {e}")
        return []

def place_order(stock_code: str, order_type: str, quantity: int, price: float = 0, order_condition: str = "00"):
    """
    매수 또는 매도 주문을 실행합니다.
    `order_type`: "01" (매도), "02" (매수) - KIS 특정 코드
    `price`: 지정가 주문에 필요. 0 또는 미제공 시 시장가 주문으로 기본 설정될 수 있음 (`order_condition`에 따라 다름).
    `order_condition`: "00" (지정가), "03" (시장가) - KIS 특정 코드
                       IOC, FOK에 대한 다른 코드 존재.
    플레이스홀더: 실제 엔드포인트, tr_id 및 파라미터는 KIS API에 따라 다릅니다.
    국내 주식 주문 예시 tr_id: TTTC0802U (매수), TTTC0801U (매도)
    """
    _ensure_token_valid() # 주문 전에 토큰 처리 확인

    # order_type (매수/매도)에 따라 tr_id 결정
    # 국내 현금 주문 예시. 해외/파생 상품은 다른 tr_id를 가집니다.
    if order_type == "02": # 매수
        tr_id = "TTTC0802U" # 현금 매수 주문
    elif order_type == "01": # 매도
        tr_id = "TTTC0801U" # 현금 매도 주문
    else:
        raise ValueError("잘못된 order_type입니다. '01'(매도) 또는 '02'(매수)여야 합니다.")

    # 계좌번호: 앞 8자리는 계좌 접두사, 뒤 2자리는 접미사.
    # .env 또는 사용자 설정 등에서 구성 필요.
    # KIS_ACCOUNT_NO_PREFIX = os.getenv("KIS_ACCOUNT_NO_PREFIX")
    # KIS_ACCOUNT_NO_SUFFIX = os.getenv("KIS_ACCOUNT_NO_SUFFIX")
    # if not KIS_ACCOUNT_NO_PREFIX or not KIS_ACCOUNT_NO_SUFFIX:
    #     raise ValueError("KIS 계좌번호 접두사와 접미사가 설정되지 않았습니다.")

    # 현재 플레이스홀더 사용. 반드시 정확하게 설정해야 함.
    CANO = KIS_APP_KEY[:8] # 플레이스홀더 - 올바르지 않음, 실제 계좌번호 사용
    ACNT_PRDT_CD = KIS_APP_KEY[-2:] # 플레이스홀더 - 올바르지 않음

    endpoint = "/api/v1/trading/order-cash" # 현금 주문 예시 엔드포인트
    payload = {
        "CANO": CANO, # 종합계좌번호 (앞 8자리)
        "ACNT_PRDT_CD": ACNT_PRDT_CD, # 계좌상품코드 (뒤 2자리)
        "PDNO": stock_code,             # 상품번호 (종목코드)
        "ORD_DVSN": order_condition,    # 주문구분 (00:지정가, 01:시장가 등 - KIS는 API에 따라 다른 코드 사용, 예: 지정가 "00", 시장가 "01". 문서 확인)
        "ORD_QTY": str(quantity),       # 주문수량
        "ORD_UNPR": str(int(price)) if price > 0 and order_condition == "00" else "0", # 주문단가 (시장가면 0)
        # "ALGO_TRAD_CLS_CODE": "", # FOK, IOC 등 옵션 (선택)
    }

    try:
        response_data = _make_api_request("POST", endpoint, data=payload, tr_id=tr_id)
        # response_data 처리. 성공적인 주문은 보통 주문 번호를 반환.
        # 예: order_no = response_data.get('output', {}).get('ODNO')
        order_output = response_data.get('output', {})
        order_no = order_output.get('ODNO') # 주문번호
        # KIS는 KRX_FWDG_ORD_ORGNO, ORD_TMD (주문시각)도 반환
        logging.info(f"{stock_code} 주문 실행됨. 유형: {order_type}, 수량: {quantity}, 가격: {price}. 주문번호: {order_no}")
        return {"success": True, "order_id": order_no, "details": order_output}
    except Exception as e:
        logging.error(f"{stock_code} 주문 실행 중 오류 발생: {e}")
        return {"success": False, "error": str(e)}

def get_account_balance():
    """
    현재 계좌 잔고 및 보유 현황을 가져옵니다.
    플레이스홀더: 실제 엔드포인트, tr_id 및 파라미터는 KIS API에 따라 다릅니다.
    국내 잔고 예시 tr_id: TTTC8434R (주식잔고조회)
                      또는 CTOS0002R (계좌 예수금/증거금 현황 조회)
    """
    # 이 tr_id는 "주식잔고합산조회"용입니다.
    # 국내 주식용: "TTTC8434R"
    # 해외 주식용: "JTTT3012R" 또는 "OD quantité" (시장에 따라 다름)
    # API 문서에서 확인 필요.
    tr_id_balance = "TTTC8434R" # 예시, 국내 주식 잔고용

    # CANO = KIS_APP_KEY[:8] # 플레이스홀더
    # ACNT_PRDT_CD = KIS_APP_KEY[-2:] # 플레이스홀더
    CANO = os.getenv("KIS_ACCOUNT_CANO", "YOUR_CANO") # 실제 계좌번호
    ACNT_PRDT_CD = os.getenv("KIS_ACCOUNT_ACNT_PRDT_CD", "01") # 실제 계좌 상품 코드

    endpoint = "/api/v1/trading/inquire-balance" # 예시 엔드포인트
    params = {
        "CANO": CANO,
        "ACNT_PRDT_CD": ACNT_PRDT_CD,
        "AFHR_FLPR_YN": "N", # 시간외단일가여부 (N: 아니요, Y: 예)
        "OFL_YN": "", # 공란
        "INQR_DVSN": "01", # 조회구분 (01: 대출일별, 02: 종목별) - 상세 보유현황은 "02" 필요할 수 있음
        "UNPR_DVSN": "01", # 단가구분 (01: 평균단가, 02: BEP단가)
        "FUND_STTL_ICLD_YN": "N", # 펀드결제분포함여부
        "FNCG_AMT_AUTO_RDPT_YN": "N", # 융자금액자동상환여부
        "PRCS_DVSN": "00", # 처리구분 (00: 전일매매포함)
        "CTX_AREA_FK100": "", # 연속조회검색조건100
        "CTX_AREA_NK100": ""  # 연속조회키100
    }

    try:
        data = _make_api_request("GET", endpoint, params=params, tr_id=tr_id_balance)
        # 데이터 처리. `output1`(보유 목록)과 `output2`(요약)로 나뉠 수 있음.
        # 예: holdings = data.get('output1', [])
        #          summary = data.get('output2', {})
        #          cash_balance = summary.get('dnca_tot_amt') # 예수금 총금액

        holdings_list = data.get('output1', [])
        summary_info = data.get('output2', []) # output2도 종종 리스트임 (항목이 하나라도)

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
                # output2에서 필요한 경우 필드 추가
            }

        # logging.info(f"계좌 잔고 조회됨. 보유 종목: {len(parsed_holdings)}개. 현금: {cash_details.get('total_cash_balance')}")
        return {"holdings": parsed_holdings, "summary": cash_details}
    except Exception as e:
        logging.error(f"계좌 잔고 조회 중 오류 발생: {e}")
        return {"holdings": [], "summary": {}, "error": str(e)}

# --- 초기화 ---
# 모듈 로드 시 또는 첫 API 호출 시 토큰 가져오기 시도.
# 지연 실행(실제 첫 API 함수 호출 시)이 더 좋을 수 있음.
# _get_access_token() # 또는 각 공개 함수 내에서 _ensure_token_valid()로 보호하여 호출

if __name__ == "__main__":
    # 이 섹션은 API 함수 직접 테스트용입니다.
    # .env 파일에 KIS_APP_KEY와 KIS_APP_SECRET 필요
    # 잔고/주문용 KIS_ACCOUNT_CANO, KIS_ACCOUNT_ACNT_PRDT_CD 필요

    # 중요: 상위 디렉토리에 .env 파일이 올바르게 설정되었는지 확인하십시오.
    # 또는 core.config가 예상하는 위치에.
    # 예:
    # KIS_APP_KEY="your_app_key"
    # KIS_APP_SECRET="your_app_secret"
    # KIS_ACCOUNT_CANO="your_account_number_first_8_digits"
    # KIS_ACCOUNT_ACNT_PRDT_CD="your_account_number_last_2_digits_product_code"

    if not KIS_APP_KEY or not KIS_APP_SECRET:
        print("환경 변수에서 KIS_APP_KEY 또는 KIS_APP_SECRET를 찾을 수 없습니다. .env 파일에 설정하십시오.")
    else:
        print(f"KIS_APP_KEY: {KIS_APP_KEY[:5]}...") # 확인을 위해 부분 키 인쇄

        # 토큰 가져오기 테스트 (다른 함수에 의해 암시적으로 호출됨)
        # if _ensure_token_valid():
        #    print(f"액세스 토큰 얻음: {ACCESS_TOKEN[:10]}...")
        # else:
        #    print("액세스 토큰을 얻는 데 실패했습니다.")
        #    exit()

        # 주가 조회 테스트 (예: 삼성전자: 005930)
        # stock_code_to_test = "005930"
        # print(f"\n{stock_code_to_test} 현재가 조회 중...")
        # price = get_stock_price(stock_code_to_test)
        # if price:
        #     print(f"{stock_code_to_test} 현재가: {price}")
        # else:
        #     print(f"{stock_code_to_test} 가격을 가져올 수 없습니다.")

        # 과거 데이터 조회 테스트
        # print(f"\n{stock_code_to_test} 과거 데이터 조회 중...")
        # historical_data = get_historical_stock_data(stock_code_to_test, "20231001", "20231020", "D")
        # if historical_data:
        #     print(f"{stock_code_to_test}에 대한 {len(historical_data)}일치 데이터 가져옴.")
        #     # print("마지막 데이터 포인트:", historical_data[-1] if historical_data else "N/A")
        # else:
        #     print(f"{stock_code_to_test} 과거 데이터를 가져올 수 없습니다.")

        # 계좌 잔고 테스트 (.env에 계좌번호 필요)
        # print("\n계좌 잔고 조회 중...")
        # balance_info = get_account_balance()
        # if "error" not in balance_info:
        #     print("계좌 잔고 요약:", balance_info.get("summary"))
        #     print("보유 종목:", balance_info.get("holdings"))
        # else:
        #     print("계좌 잔고를 가져올 수 없습니다:", balance_info.get("error"))

        # 주문 실행 테스트 (매우 주의하여 사용, 가급적 모의 투자 계좌에서)
        # print("\n**테스트** 주문 시도 중 (모의 투자 환경 확인)...")
        # 참고: 실제 주문 시 모든 파라미터(종목코드, 수량, 가격, 주문조건, 계좌정보)가 정확한지 확인하십시오.
        # 이것은 시장가로 "005930" 주식 1주에 대한 가상 매수 주문입니다.
        # .env에 KIS_ACCOUNT_CANO와 KIS_ACCOUNT_ACNT_PRDT_CD가 설정되었는지 확인하십시오.
        # test_order_stock = "005930" # 삼성전자
        # test_order_result = place_order(
        #     stock_code=test_order_stock,
        #     order_type="02",  # 매수
        #     quantity=1,
        #     price=0,          # 시장가 주문 시 가격은 0
        #     order_condition="03" # 시장가 주문 ("시장가") - KIS 코드는 다를 수 있음, "주문구분" 확인
        # )
        # print("테스트 주문 결과:", test_order_result)
        pass # 기본 테스트 블록 끝

    print("플레이스홀더 core/kis_api.py가 함수 구조와 함께 생성되었습니다.")
    print("실제 구현에는 엔드포인트, 요청/응답 형식 및 인증에 대한 KIS API 문서가 필요합니다.")
    print("개발 및 테스트에는 가상 거래 URL(openapivts.koreainvestment.com)을 사용하십시오.")
    print("이 파일에는 토큰 가져오기, 가격 조회, 과거 데이터 조회, 주문 실행, 잔고 확인 예제가 포함되어 있습니다.")
    print("로깅도 포함되어 있습니다.")
    print("__main__ 블록이 함수 기본 테스트용으로 추가되었습니다 (현재 주석 처리됨).")
