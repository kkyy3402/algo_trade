import pandas as pd
from datetime import datetime, timedelta
import logging

# Assuming kis_api and indicators are in the 'core' directory,
# and this service is in the 'services' directory.
# Adjust import paths if project structure is different or if using a different module organization.
# For now, assuming a common root package or PYTHONPATH setup that allows these imports.
# If 'backend' is the root, then from backend.core import ...
from core import kis_api  # Placeholder, might need adjustment based on Python path
from core import indicators # Placeholder

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Default parameters for indicators (can be made configurable)
BB_WINDOW = 20
BB_STD_DEV = 2
WILLIAMS_R_PERIOD = 14

# Williams %R thresholds (configurable)
WILLIAMS_R_OVERSOLD = -80
WILLIAMS_R_OVERBOUGHT = -20

class TradingService:
    def __init__(self, kis_api_client=None):
        """
        Initializes the TradingService.
        Optionally accepts a KIS API client instance for easier testing/mocking.
        """
        self.kis_client = kis_api_client if kis_api_client else kis_api # Use the imported module by default
        # In a more complex app, KIS client might be injected.

    def _fetch_and_prepare_data(self, stock_code: str, days_history: int = 60) -> pd.DataFrame:
        """
        Fetches historical data and prepares it for indicator calculation.
        `days_history`: Number of days of historical data to fetch for calculations.
        """
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days_history + BB_WINDOW) # Fetch a bit more for initial calculations

        logger.info(f"Fetching historical data for {stock_code} from {start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')}")

        # KIS API returns data with 'date' in 'YYYYMMDD' format.
        # The historical_data is expected to be a list of dicts like:
        # {'date': '20231020', 'open': 70000.0, 'high': 71000.0, 'low': 69000.0, 'close': 70500.0, 'volume': 123456}
        raw_data = self.kis_client.get_historical_stock_data(
            stock_code,
            start_date.strftime("%Y%m%d"),
            end_date.strftime("%Y%m%d")
        )

        if not raw_data:
            logger.warning(f"No historical data received for {stock_code}.")
            return pd.DataFrame()

        df = pd.DataFrame(raw_data)
        if df.empty:
            logger.warning(f"Historical data for {stock_code} is empty after DataFrame conversion.")
            return pd.DataFrame()

        # Convert columns to appropriate types
        df['date'] = pd.to_datetime(df['date'], format='%Y%m%d')
        numeric_cols = ['open', 'high', 'low', 'close', 'volume']
        for col in numeric_cols:
            df[col] = pd.to_numeric(df[col], errors='coerce')

        df.sort_values(by='date', inplace=True)
        df.set_index('date', inplace=True) # Important for TA libraries

        logger.info(f"Successfully prepared {len(df)} data points for {stock_code}.")
        return df

    def analyze_stock(self, stock_code: str):
        """
        Analyzes a single stock for trading signals based on Bollinger Bands and Williams %R.
        Returns a dictionary with the stock code, current price, signal, and reason.
        Example signal: {"stock_code": "005930", "price": 70000, "signal": "BUY", "reason": "Price below lower BB and WR oversold."}
                       {"stock_code": "005930", "price": 72000, "signal": "HOLD", "reason": "No clear signal."}
        """
        logger.info(f"Analyzing stock: {stock_code}")

        # 1. Fetch current price (not strictly needed for signal generation from historical, but good for context)
        current_price_raw = self.kis_client.get_stock_price(stock_code)
        current_price = float(current_price_raw) if current_price_raw is not None else None

        if current_price is None:
            logger.warning(f"Could not get current price for {stock_code}. Skipping analysis.")
            return {"stock_code": stock_code, "price": None, "signal": "ERROR", "reason": "Failed to fetch current price."}

        # 2. Fetch historical data
        # For BB(20) and WR(14), we need at least 20 periods for BB, 14 for WR.
        # Fetching more to ensure enough data for calculations and to get a recent signal.
        df_history = self._fetch_and_prepare_data(stock_code, days_history=BB_WINDOW + WILLIAMS_R_PERIOD + 5)

        if df_history.empty or len(df_history) < max(BB_WINDOW, WILLIAMS_R_PERIOD):
            logger.warning(f"Not enough historical data for {stock_code} to perform analysis (need {max(BB_WINDOW, WILLIAMS_R_PERIOD)}, got {len(df_history)}).")
            return {"stock_code": stock_code, "price": current_price, "signal": "NO_DATA", "reason": "Insufficient historical data."}

        # 3. Calculate Indicators
        df_with_bb = indicators.calculate_bollinger_bands(df_history.copy(), window=BB_WINDOW, window_dev=BB_STD_DEV)
        df_with_indicators = indicators.calculate_williams_r(df_with_bb, period=WILLIAMS_R_PERIOD)

        # Get the latest indicator values
        latest_data = df_with_indicators.iloc[-1]

        # Ensure all required indicator values are present
        required_indicator_cols = ['close', 'bb_lband', 'bb_hband', 'wr']
        if latest_data[required_indicator_cols].isnull().any():
            logger.warning(f"Could not calculate all required indicators for {stock_code} for the latest period. Data: {latest_data[required_indicator_cols]}")
            return {"stock_code": stock_code, "price": current_price, "signal": "NO_INDICATOR", "reason": "Failed to calculate indicators for the latest period."}

        last_close = latest_data['close']
        lower_band = latest_data['bb_lband']
        upper_band = latest_data['bb_hband']
        william_r = latest_data['wr']

        logger.info(f"{stock_code} - Last Close: {last_close}, Lower BB: {lower_band}, Upper BB: {upper_band}, Williams %R: {william_r}")

        # 4. Apply Trading Rules (using the latest available data point)
        signal = "HOLD"
        reason = "No clear signal based on current strategy."

        # Buy Signal Logic (example)
        # Price crosses *below* lower Bollinger Band (or is near it) AND Williams %R indicates oversold
        if last_close < lower_band and william_r < WILLIAMS_R_OVERSOLD:
            signal = "BUY"
            reason = f"Price ({last_close:.2f}) below lower BB ({lower_band:.2f}) and Williams %R ({william_r:.2f} < {WILLIAMS_R_OVERSOLD}) indicates oversold."

        # Sell Signal Logic (example)
        # Price crosses *above* upper Bollinger Band (or is near it) AND Williams %R indicates overbought
        elif last_close > upper_band and william_r > WILLIAMS_R_OVERBOUGHT:
            signal = "SELL"
            reason = f"Price ({last_close:.2f}) above upper BB ({upper_band:.2f}) and Williams %R ({william_r:.2f} > {WILLIAMS_R_OVERBOUGHT}) indicates overbought."

        # Consider other conditions, e.g., if already holding the stock for sell signals,
        # or available cash for buy signals. This basic version just generates the signal.

        return {
            "stock_code": stock_code,
            "timestamp": latest_data.name.isoformat() if latest_data.name else datetime.now().isoformat(), # data point's timestamp
            "price_at_signal": last_close, # Price at the time of signal generation (from historical data)
            "current_market_price": current_price, # Most recent market price (might differ slightly)
            "signal": signal,
            "reason": reason,
            "indicators": {
                "bollinger_lower": lower_band,
                "bollinger_middle": latest_data.get('bb_mavg'),
                "bollinger_upper": upper_band,
                "williams_r": william_r
            }
        }

    def scan_stocks(self, stock_codes: list[str]):
        """
        Scans a list of stocks and returns analysis results for each.
        """
        results = []
        for code in stock_codes:
            try:
                analysis = self.analyze_stock(code)
                results.append(analysis)
            except Exception as e:
                logger.error(f"Error analyzing stock {code}: {e}", exc_info=True)
                results.append({
                    "stock_code": code,
                    "signal": "ERROR",
                    "reason": f"An unexpected error occurred during analysis: {str(e)}"
                })
        return results

    def execute_order(self, stock_code: str, order_type: str, quantity: int, price: float, order_condition: str):
        """
        Executes a trade order using the KIS API client.
        Maps directly to kis_api.place_order.
        """
        logger.info(f"TradingService: Executing order for {stock_code}, Type: {order_type}, Qty: {quantity}")
        if not self.kis_client:
            logger.error("KIS client not available in TradingService for executing order.")
            return {"success": False, "error": "KIS client not configured."}

        return self.kis_client.place_order(
            stock_code=stock_code,
            order_type=order_type,
            quantity=quantity,
            price=price,
            order_condition=order_condition
        )

    def get_portfolio_details(self):
        """
        Retrieves account balance and holdings using the KIS API client.
        Maps directly to kis_api.get_account_balance.
        """
        logger.info("TradingService: Retrieving portfolio details.")
        if not self.kis_client:
            logger.error("KIS client not available in TradingService for fetching portfolio.")
            return {"error": "KIS client not configured.", "holdings": [], "summary": {}}

        return self.kis_client.get_account_balance()

# --- Potential Strategy Pattern Implementation ---
# To make the trading logic more extensible (e.g., adding new strategies easily),
# the Strategy pattern could be implemented as follows:
#
# 1. Define a Strategy Interface (Abstract Base Class):
#    from abc import ABC, abstractmethod
#    class TradingStrategy(ABC):
#        @abstractmethod
#        def analyze(self, stock_code: str, data: pd.DataFrame, current_price: float) -> dict:
#            """
#            Analyzes stock data and returns a trading signal.
#            The returned dict should be compatible with the TradingSignal model.
#            """
#            pass
#
# 2. Implement Concrete Strategies:
#    class BollingerWilliamsStrategy(TradingStrategy):
#        def __init__(self, bb_window=20, bb_std_dev=2, wr_period=14, wr_oversold=-80, wr_overbought=-20):
#            self.bb_window = bb_window
#            # ... other params
#
#        def analyze(self, stock_code: str, data: pd.DataFrame, current_price: float) -> dict:
#            df_with_bb = indicators.calculate_bollinger_bands(data.copy(), window=self.bb_window, ...)
#            df_with_indicators = indicators.calculate_williams_r(df_with_bb, period=self.wr_period)
#            latest_data = df_with_indicators.iloc[-1]
#            # ... (current logic from analyze_stock) ...
#            # return {"stock_code": stock_code, "signal": ..., "reason": ..., ...}
#
#    class MovingAverageCrossoverStrategy(TradingStrategy):
#        # ... implementation for another strategy ...
#        pass
#
# 3. Modify TradingService to use a strategy:
#    class TradingService:
#        def __init__(self, kis_api_client=None, strategy: TradingStrategy = None):
#            self.kis_client = kis_api_client or kis_api
#            # Default to BollingerWilliamsStrategy if none provided, or make it mandatory
#            self.strategy = strategy or BollingerWilliamsStrategy()
#
#        def analyze_stock(self, stock_code: str): # This method would change significantly
#            logger.info(f"Analyzing stock: {stock_code} using {self.strategy.__class__.__name__}")
#            current_price_raw = self.kis_client.get_stock_price(stock_code) # ...
#            df_history = self._fetch_and_prepare_data(stock_code, ...) # ...
#            if df_history.empty or ...:
#                # ... handle no data ...
#
#            # Delegate analysis to the current strategy instance
#            signal_data = self.strategy.analyze(stock_code, df_history, float(current_price_raw) if current_price_raw else 0.0)
#            return signal_data
#
#        def set_strategy(self, strategy: TradingStrategy):
#            logger.info(f"Switching trading strategy to: {strategy.__class__.__name__}")
#            self.strategy = strategy
# --- End of Potential Strategy Pattern ---

# Example Usage (for testing this service directly)
if __name__ == '__main__':
    logger.info("Testing TradingService...")

    # Mock KIS API client for testing without real API calls
    class MockKISAPI:
        def get_stock_price(self, stock_code: str):
            logger.info(f"[MockKISAPI] Getting price for {stock_code}")
            if stock_code == "005930": return 70000.0 # Samsung Electronics
            if stock_code == "035720": return 120000.0 # Kakao
            return None

        def get_historical_stock_data(self, stock_code: str, start_date: str, end_date: str, period_code: str = "D"):
            logger.info(f"[MockKISAPI] Getting historical data for {stock_code} from {start_date} to {end_date}")
            # Generate some dummy data that might trigger signals
            dates = pd.date_range(start=start_date, end=end_date, freq='B') # Business days
            count = len(dates)
            if count == 0: return []

            data = []
            price = 100
            for i, date_val in enumerate(dates):
                # Simple pattern: down then up for potential buy, then up then down for potential sell
                if stock_code == "005930": # For Samsung (potential buy)
                    if i < count / 2:
                        price *= 0.98 # Price goes down
                    else:
                        price *= 1.01 # Price goes up
                elif stock_code == "035720": # For Kakao (potential sell)
                    if i < count / 2:
                        price *= 1.02 # Price goes up
                    else:
                        price *= 0.99 # Price goes down
                else:
                    price *= (1 + (i % 3 - 1) * 0.02) # Generic fluctuation

                data.append({
                    'date': date_val.strftime('%Y%m%d'),
                    'open': price * 0.99,
                    'high': price * 1.02,
                    'low': price * 0.98,
                    'close': price,
                    'volume': 1000 + i * 10
                })
            return data

    # If you want to test with the actual KIS API (USE VIRTUAL ACCOUNT and ensure .env is set up)
    # from core.config import KIS_APP_KEY, KIS_APP_SECRET # Make sure .env is loaded
    # if KIS_APP_KEY and KIS_APP_SECRET:
    #     print("Using actual KIS API for service test.")
    #     live_kis_client = kis_api
    #     trading_service_instance = TradingService(kis_api_client=live_kis_client)
    # else:
    #     print("KIS API keys not found, using MockKISAPI for service test.")
    #     mock_kis_client = MockKISAPI()
    #     trading_service_instance = TradingService(kis_api_client=mock_kis_client)

    # Using Mock for safety by default
    mock_kis_client = MockKISAPI()
    trading_service_instance = TradingService(kis_api_client=mock_kis_client)

    # stocks_to_scan = ["005930", "035720", "000660"] # Samsung, Kakao, SK Hynix (example)
    stocks_to_scan = ["005930", "035720"]

    logger.info(f"Scanning stocks: {stocks_to_scan}")
    analysis_results = trading_service_instance.scan_stocks(stocks_to_scan)

    for result in analysis_results:
        print(f"--- Analysis for {result.get('stock_code')} ---")
        print(f"  Timestamp: {result.get('timestamp')}")
        print(f"  Price at Signal: {result.get('price_at_signal')}")
        print(f"  Current Market Price: {result.get('current_market_price')}")
        print(f"  Signal: {result.get('signal')}")
        print(f"  Reason: {result.get('reason')}")
        if result.get('indicators'):
            print(f"  Indicators:")
            print(f"    BB Lower: {result['indicators'].get('bollinger_lower'):.2f}")
            print(f"    BB Middle: {result['indicators'].get('bollinger_middle'):.2f}")
            print(f"    BB Upper: {result['indicators'].get('bollinger_upper'):.2f}")
            print(f"    Williams %R: {result['indicators'].get('williams_r'):.2f}")
        print("--------------------")
