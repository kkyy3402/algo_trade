from abc import ABC, abstractmethod
import pandas as pd
import logging
# 'core.indicators'가 프로젝트 구조에 상대적인 정확한 경로라고 가정합니다.
# 'backend'가 Python 경로의 루트이면 'backend.core.indicators'가 됩니다.
# 현재 TradingService에서처럼 'core.indicators'를 사용합니다.
from core import indicators

logger = logging.getLogger(__name__)

# 지표 기본 파라미터 (전략 인스턴스별 설정 가능)
BB_WINDOW = 20
BB_STD_DEV = 2
WILLIAMS_R_PERIOD = 14
WILLIAMS_R_OVERSOLD = -80
WILLIAMS_R_OVERBOUGHT = -20


class TradingStrategy(ABC):
    """
    추상 기본 클래스로, 다양한 트레이딩 전략을 정의하기 위한 인터페이스 역할을 합니다.
    모든 구체적인 전략 클래스는 이 클래스를 상속받아 'analyze' 메소드를 구현해야 합니다.
    """
    @abstractmethod
    def analyze(self, stock_code: str, data: pd.DataFrame, current_price: float) -> dict:
        """
        주어진 주식 데이터를 분석하여 트레이딩 시그널(매수, 매도, 보류)과 관련 정보를 반환합니다.

        Args:
            stock_code (str): 분석할 주식의 종목 코드.
            data (pd.DataFrame): 분석에 사용될 과거 주가 데이터 (OHLCV 포함, 날짜 인덱스).
            current_price (float): 현재 주가 (참고용).

        Returns:
            dict: 트레이딩 시그널 정보를 담은 딕셔너리.
                  예: {'stock_code': '005930', 'signal': 'BUY', 'reason': '...', 'indicators': {...}}
                  이 딕셔너리는 models.trade.TradingSignal Pydantic 모델과 호환되어야 합니다.
        """
        pass


class BollingerWilliamsStrategy(TradingStrategy):
    """
    볼린저 밴드와 Williams %R 지표를 사용하는 트레이딩 전략입니다.
    """
    def __init__(self,
                 bb_window: int = BB_WINDOW,
                 bb_std_dev: int = BB_STD_DEV,
                 wr_period: int = WILLIAMS_R_PERIOD,
                 wr_oversold: float = WILLIAMS_R_OVERSOLD,
                 wr_overbought: float = WILLIAMS_R_OVERBOUGHT):
        self.bb_window = bb_window
        self.bb_std_dev = bb_std_dev
        self.wr_period = wr_period
        self.wr_oversold = wr_oversold
        self.wr_overbought = wr_overbought
        logger.info(f"BollingerWilliamsStrategy 초기화: BB창={bb_window}, BB표준편차={bb_std_dev}, WR기간={wr_period}, WR과매도={wr_oversold}, WR과매수={wr_overbought}")

    def analyze(self, stock_code: str, data: pd.DataFrame, current_price: float) -> dict:
        """
        볼린저 밴드와 Williams %R 지표를 기반으로 주식 데이터를 분석합니다.
        """
        if data.empty or len(data) < max(self.bb_window, self.wr_period):
            logger.warning(f"[{stock_code}] BollingerWilliamsStrategy: 분석을 위한 데이터 부족 (필요: {max(self.bb_window, self.wr_period)}, 보유: {len(data)}).")
            return {
                "stock_code": stock_code, "price_at_signal": None, "current_market_price": current_price,
                "signal": "NO_DATA", "reason": "분석을 위한 과거 데이터 부족.", "indicators": {}
            }

        # 지표 계산
        df_with_bb = indicators.calculate_bollinger_bands(data.copy(), window=self.bb_window, window_dev=self.bb_std_dev)
        df_with_indicators = indicators.calculate_williams_r(df_with_bb, period=self.wr_period)

        latest_data = df_with_indicators.iloc[-1]

        required_indicator_cols = ['close', 'bb_lband', 'bb_hband', 'wr']
        if latest_data[required_indicator_cols].isnull().any():
            logger.warning(f"[{stock_code}] BollingerWilliamsStrategy: 최신 기간에 대한 지표 계산 실패. 데이터: {latest_data[required_indicator_cols]}")
            return {
                "stock_code": stock_code, "price_at_signal": latest_data.get('close'), "current_market_price": current_price,
                "signal": "NO_INDICATOR", "reason": "최신 기간에 대한 지표 계산 실패.",
                "indicators": {
                    "bollinger_lower": latest_data.get('bb_lband'), "bollinger_middle": latest_data.get('bb_mavg'),
                    "bollinger_upper": latest_data.get('bb_hband'), "williams_r": latest_data.get('wr')
                }
            }

        last_close = latest_data['close']
        lower_band = latest_data['bb_lband']
        upper_band = latest_data['bb_hband']
        william_r = latest_data['wr']

        logger.info(f"[{stock_code}] BollingerWilliamsStrategy - 최종 종가: {last_close:.2f}, BB하단: {lower_band:.2f}, BB상단: {upper_band:.2f}, Williams %R: {william_r:.2f}")

        signal = "HOLD"
        reason = "현재 전략에 따른 명확한 시그널 없음."

        # 매수 시그널 로직
        if last_close < lower_band and william_r < self.wr_oversold:
            signal = "BUY"
            reason = f"가격({last_close:.2f})이 BB하단({lower_band:.2f})보다 낮고, Williams %R({william_r:.2f} < {self.wr_oversold:.2f})이 과매도 상태."

        # 매도 시그널 로직
        elif last_close > upper_band and william_r > self.wr_overbought:
            signal = "SELL"
            reason = f"가격({last_close:.2f})이 BB상단({upper_band:.2f})보다 높고, Williams %R({william_r:.2f} > {self.wr_overbought:.2f})이 과매수 상태."

        return {
            "stock_code": stock_code,
            "timestamp": latest_data.name.isoformat() if latest_data.name else pd.Timestamp.now().isoformat(),
            "price_at_signal": last_close,
            "current_market_price": current_price,
            "signal": signal,
            "reason": reason,
            "indicators": {
                "bollinger_lower": lower_band,
                "bollinger_middle": latest_data.get('bb_mavg'),
                "bollinger_upper": upper_band,
                "williams_r": william_r
            }
        }

# 여기에 다른 전략들을 추가할 수 있습니다.
# 예: class MovingAverageCrossoverStrategy(TradingStrategy): ...

if __name__ == '__main__':
    # 전략 테스트용 샘플 데이터 (TradingService의 테스트 코드에서 가져옴)
    sample_ohlcv = {
        'open': [100, 102, 101, 103, 105, 104, 102, 100, 98, 99, 101, 103, 102, 105, 107, 108, 106, 105, 109, 110, 108, 106, 103, 100, 98],
        'high': [103, 104, 103, 105, 106, 105, 104, 102, 100, 101, 103, 105, 104, 107, 109, 110, 108, 107, 110, 112, 110, 108, 105, 102, 100],
        'low':  [99, 101, 100, 102, 103, 102, 101, 99, 97, 98, 100, 101, 100, 104, 106, 107, 105, 104, 108, 109, 107, 105, 102, 99, 97],
        'close':[101, 103, 102, 104, 105, 103, 102, 101, 99, 100, 102, 104, 103, 106, 108, 107, 106, 106, 109, 111, 109, 107, 104, 101, 99],
        'volume':[1000,1100,1050,1200,1250,1150,1100,1000,950,980,1020,1150,1100,1300,1350,1400,1200,1150,1450,1500,1300,1200,1000,900,850]
    }
    dates = pd.date_range(start='2023-01-01', periods=len(sample_ohlcv['close']), freq='B')
    df_test = pd.DataFrame(sample_ohlcv, index=dates)

    strategy_test = BollingerWilliamsStrategy()
    analysis_result = strategy_test.analyze("000TEST", df_test, df_test.iloc[-1]['close'])

    logger.info("BollingerWilliamsStrategy 테스트 실행 결과:")
    import json
    logger.info(json.dumps(analysis_result, indent=2, ensure_ascii=False))
