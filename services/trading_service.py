import pandas as pd
from datetime import datetime, timedelta
import logging

from core import kis_api
# from core import indicators # TradingService에서 분석 로직에 직접 사용되지 않음
from .strategies import TradingStrategy, BollingerWilliamsStrategy # 전략 임포트

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# 데이터 조회 기본 파라미터 (설정 가능)
# BB_WINDOW와 WILLIAMS_R_PERIOD는 이제 전략 기본값의 일부이지만, _fetch_and_prepare_data에 필요함
# 충분한 데이터를 가져오도록 보장. 전략 인스턴스에서 가져오는 것이 더 좋은 방법일 수 있음.
DEFAULT_BB_WINDOW_FOR_FETCH = 20
DEFAULT_WR_PERIOD_FOR_FETCH = 14


class TradingService:
    def __init__(self, kis_api_client=None, strategy: TradingStrategy = None):
        """
        TradingService를 초기화합니다.

        Args:
            kis_api_client: KIS API 클라이언트 인스턴스. 제공되지 않으면 core.kis_api 모듈을 사용합니다.
            strategy (TradingStrategy): 사용할 트레이딩 전략 인스턴스.
                                       제공되지 않으면 BollingerWilliamsStrategy를 기본으로 사용합니다.
        """
        self.kis_client = kis_api_client if kis_api_client else kis_api
        self.strategy = strategy if strategy else BollingerWilliamsStrategy()
        logger.info(f"TradingService가 다음 전략으로 초기화되었습니다: {self.strategy.__class__.__name__}")

    def set_strategy(self, strategy: TradingStrategy):
        """
        트레이딩 전략을 변경합니다.
        """
        logger.info(f"TradingService: 전략 변경 -> {strategy.__class__.__name__}")
        self.strategy = strategy

    def _fetch_and_prepare_data(self, stock_code: str, days_history: int = 60) -> pd.DataFrame:
        """
        지표 계산을 위해 과거 데이터를 가져와 준비합니다.
        `days_history`: 계산을 위해 가져올 과거 데이터의 일수.
                       전략에 필요한 최소 기간보다 충분히 길어야 합니다.
        """
        # 전략 객체에서 필요한 최소 데이터 기간을 가져올 수 있다면 더 좋습니다.
        # 예: required_days = self.strategy.get_required_data_length() or (DEFAULT_BB_WINDOW_FOR_FETCH + DEFAULT_WR_PERIOD_FOR_FETCH)
        # 현재는 고정값을 사용합니다.
        required_buffer = 30 # 추가 버퍼
        effective_days_history = max(days_history, DEFAULT_BB_WINDOW_FOR_FETCH + DEFAULT_WR_PERIOD_FOR_FETCH + required_buffer)

        end_date = datetime.now()
        # KIS API는 일반적으로 YYYYMMDD 형식을 사용합니다.
        start_date_str = (end_date - timedelta(days=effective_days_history)).strftime("%Y%m%d")
        end_date_str = end_date.strftime("%Y%m%d")

        logger.info(f"[{stock_code}] TradingService: 과거 데이터 조회 ({start_date_str} ~ {end_date_str})")

        raw_data = self.kis_client.get_historical_stock_data(
            stock_code,
            start_date_str,
            end_date_str
        )

        if not raw_data:
            logger.warning(f"[{stock_code}] TradingService: {stock_code}에 대한 과거 데이터 없음.")
            return pd.DataFrame()

        df = pd.DataFrame(raw_data)
        if df.empty:
            logger.warning(f"[{stock_code}] TradingService: DataFrame 변환 후 {stock_code} 과거 데이터 비어있음.")
            return pd.DataFrame()

        df['date'] = pd.to_datetime(df['date'], format='%Y%m%d')
        numeric_cols = ['open', 'high', 'low', 'close', 'volume']
        for col in numeric_cols:
            df[col] = pd.to_numeric(df[col], errors='coerce')

        df.sort_values(by='date', inplace=True)
        df.set_index('date', inplace=True)

        logger.info(f"[{stock_code}] TradingService: {stock_code}에 대해 {len(df)}개 데이터 포인트 준비 완료.")
        return df

    def analyze_stock(self, stock_code: str):
        """
        현재 설정된 전략을 사용하여 단일 주식을 분석합니다.
        """
        logger.info(f"[{stock_code}] TradingService: 주식 분석 시작 (전략: {self.strategy.__class__.__name__})")

        current_price_raw = self.kis_client.get_stock_price(stock_code)
        current_price = float(current_price_raw) if current_price_raw is not None else 0.0

        if current_price_raw is None: # 현재가 조회 실패 시 분석을 중단할 수 있습니다.
            logger.warning(f"[{stock_code}] TradingService: 현재가를 가져올 수 없어 분석 중단. ({stock_code})")
            return {
                "stock_code": stock_code, "price_at_signal": None, "current_market_price": None,
                "signal": "ERROR", "reason": "현재가 조회 실패.", "indicators": {}
            }

        # 전략에 충분한 데이터 조회. 전략 자체가 이 요구사항을 정의할 수 있음.
        # 현재는 일반 버퍼 사용.
        df_history = self._fetch_and_prepare_data(stock_code, days_history=90) # 충분한 데이터 조회

        if df_history.empty:
            logger.warning(f"[{stock_code}] TradingService: 분석을 위한 과거 데이터 부족 ({stock_code}).")
            # TradingSignal Pydantic 모델과 호환되는 구조 반환
            return {
                "stock_code": stock_code, "price_at_signal": None, "current_market_price": current_price,
                "signal": "NO_DATA", "reason": "분석을 위한 과거 데이터 부족.", "indicators": {}
            }

        # 분석을 전략 객체에 위임
        analysis_result = self.strategy.analyze(stock_code, df_history, current_price)
        return analysis_result

    def scan_stocks(self, stock_codes: list[str]):
        """
        주식 목록을 스캔하고 각 주식에 대한 분석 결과를 반환합니다.
        """
        results = []
        for code in stock_codes:
            try:
                analysis = self.analyze_stock(code)
                results.append(analysis)
            except Exception as e:
                logger.error(f"[{code}] TradingService: 주식 분석 중 오류 발생 ({code}): {e}", exc_info=True)
                results.append({
                    "stock_code": code,
                    "signal": "ERROR",
                    "reason": f"분석 중 예기치 않은 오류 발생: {str(e)}",
                    "price_at_signal": None, "current_market_price": None, "indicators": {}
                })
        return results

    def execute_order(self, stock_code: str, order_type: str, quantity: int, price: float, order_condition: str):
        """
        KIS API 클라이언트를 사용하여 거래 주문을 실행합니다.
        kis_api.place_order에 직접 매핑됩니다.
        """
        logger.info(f"TradingService: 주문 실행 {stock_code}, 유형: {order_type}, 수량: {quantity}")
        if not self.kis_client:
            logger.error("TradingService: 주문 실행을 위한 KIS 클라이언트 없음.")
            return {"success": False, "error": "KIS 클라이언트가 설정되지 않았습니다."}

        return self.kis_client.place_order(
            stock_code=stock_code,
            order_type=order_type,
            quantity=quantity,
            price=price,
            order_condition=order_condition
        )

    def get_portfolio_details(self):
        """
        KIS API 클라이언트를 사용하여 계좌 잔고 및 보유 현황을 조회합니다.
        kis_api.get_account_balance에 직접 매핑됩니다.
        """
        logger.info("TradingService: 포트폴리오 상세 정보 조회.")
        if not self.kis_client:
            logger.error("TradingService: 포트폴리오 조회를 위한 KIS 클라이언트 없음.")
            return {"error": "KIS 클라이언트가 설정되지 않았습니다.", "holdings": [], "summary": {}}

        return self.kis_client.get_account_balance()

# 이전에 Strategy Pattern 관련 주석은 strategies.py로 개념이 이전되었으므로 여기서는 제거합니다.
# __main__ 테스트 블록은 유지하되, Strategy를 주입하도록 수정이 필요합니다.

if __name__ == '__main__':
    logger.info("TradingService 테스트 (Strategy Pattern 적용)...")

    # 테스트용 Mock KIS API 클라이언트
    class MockKISAPI:
        def get_stock_price(self, stock_code: str):
            logger.info(f"[MockKISAPI] {stock_code} 가격 조회")
            if stock_code == "005930": return 70000.0
            return 10000.0 # 기본값

        def get_historical_stock_data(self, stock_code: str, start_date: str, end_date: str, period_code: str = "D"):
            logger.info(f"[MockKISAPI] {stock_code} 과거 데이터 조회 ({start_date} ~ {end_date})")
            dates = pd.date_range(start=start_date, end=end_date, freq='B')
            count = len(dates)
            if count == 0: return []

            data = []
            price = 10000
            for i, date_val in enumerate(dates):
                price *= (1 + (i % 5 - 2) * 0.01) # 약간의 변동성
                data.append({
                    'date': date_val.strftime('%Y%m%d'),
                    'open': price * 0.99, 'high': price * 1.02,
                    'low': price * 0.98, 'close': price, 'volume': 1000 + i * 10
                })
            return data

    mock_kis_client = MockKISAPI()

    # 사용할 전략 인스턴스 생성
    default_strategy = BollingerWilliamsStrategy()

    # 전략을 주입하여 TradingService 인스턴스 생성
    trading_service_instance = TradingService(kis_api_client=mock_kis_client, strategy=default_strategy)

    stocks_to_scan = ["005930", "035720"]

    logger.info(f"스캔할 주식: {stocks_to_scan}")
    analysis_results = trading_service_instance.scan_stocks(stocks_to_scan)

    import json
    for result in analysis_results:
        logger.info(f"--- {result.get('stock_code')} 분석 결과 ---")
        logger.info(json.dumps(result, indent=2, ensure_ascii=False))
        logger.info("---------------------------")
