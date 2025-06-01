import pytest
import pandas as pd
from unittest.mock import MagicMock, patch # MagicMock for mocking objects, patch for functions/modules

from services.trading_service import TradingService
from services.strategies import TradingStrategy, BollingerWilliamsStrategy # For type hinting and default strategy

# Helper to create sample OHLCV data list (like KIS API might return)
def create_sample_raw_ohlcv_list(num_rows=30):
    return [
        {
            'date': (pd.Timestamp('2023-01-01') + pd.Timedelta(days=i)).strftime('%Y%m%d'),
            'open': float(100 + i), 'high': float(105 + i), 'low': float(95 + i),
            'close': float(100 + i), 'volume': int(1000 + i * 10)
        } for i in range(num_rows)
    ]

class TestTradingService:
    @pytest.fixture
    def mock_kis_client(self):
        client = MagicMock()
        client.get_stock_price.return_value = "12000" # String, as KIS API might return
        client.get_historical_stock_data.return_value = create_sample_raw_ohlcv_list(40)
        client.place_order.return_value = {"success": True, "order_id": "ORD123", "details": {}}
        client.get_account_balance.return_value = {"holdings": [], "summary": {"total_cash_balance": 1000000.0}}
        return client

    @pytest.fixture
    def mock_strategy(self):
        strategy = MagicMock(spec=TradingStrategy) # spec ensures it has methods of TradingStrategy
        strategy.analyze.return_value = {
            "stock_code": "005930", "signal": "BUY", "reason": "Mocked strategy buy signal",
            "price_at_signal": 110.0, "current_market_price": 110.0,
            "indicators": {"mock_indicator": 1.0}
        }
        # strategy.__class__.__name__ = "MockStrategy" # For logging
        return strategy

    def test_trading_service_initialization(self, mock_kis_client, mock_strategy):
        """TradingService 초기화 테스트 (KIS 클라이언트 및 전략 주입)"""
        service = TradingService(kis_api_client=mock_kis_client, strategy=mock_strategy)
        assert service.kis_client is mock_kis_client
        assert service.strategy is mock_strategy
        print("TradingService 초기화 (mock 클라이언트, mock 전략) 테스트 통과")

        # 기본 전략 사용 테스트
        service_default_strategy = TradingService(kis_api_client=mock_kis_client)
        assert isinstance(service_default_strategy.strategy, BollingerWilliamsStrategy)
        print("TradingService 초기화 (기본 전략) 테스트 통과")

    def test_fetch_and_prepare_data(self, mock_kis_client):
        """_fetch_and_prepare_data 메소드 테스트"""
        service = TradingService(kis_api_client=mock_kis_client) # Default strategy is fine here
        df = service._fetch_and_prepare_data("005930", days_history=30)

        mock_kis_client.get_historical_stock_data.assert_called_once()
        assert not df.empty
        assert isinstance(df.index, pd.DatetimeIndex)
        assert 'close' in df.columns
        assert pd.api.types.is_numeric_dtype(df['close'])
        print("_fetch_and_prepare_data 테스트 통과")

    def test_analyze_stock(self, mock_kis_client, mock_strategy):
        """analyze_stock 메소드가 strategy.analyze를 호출하는지 테스트"""
        service = TradingService(kis_api_client=mock_kis_client, strategy=mock_strategy)
        stock_code = "005930"
        result = service.analyze_stock(stock_code)

        mock_kis_client.get_stock_price.assert_called_with(stock_code)
        # _fetch_and_prepare_data 내에서 get_historical_stock_data 호출됨
        mock_kis_client.get_historical_stock_data.assert_called()
        mock_strategy.analyze.assert_called_once()
        # analyze의 첫번째 인자가 stock_code인지, 두번째가 DataFrame인지 등도 확인 가능
        # args, _ = mock_strategy.analyze.call_args
        # assert args[0] == stock_code
        # assert isinstance(args[1], pd.DataFrame)

        assert result["signal"] == "BUY" # Mocked strategy의 반환값 확인
        assert result["reason"] == "Mocked strategy buy signal"
        print("analyze_stock (mock 전략 사용) 테스트 통과")

    def test_analyze_stock_no_current_price(self, mock_kis_client, mock_strategy):
        """현재가 조회 실패 시 analyze_stock 동작 테스트"""
        mock_kis_client.get_stock_price.return_value = None # 현재가 조회 실패 시뮬레이션
        service = TradingService(kis_api_client=mock_kis_client, strategy=mock_strategy)
        result = service.analyze_stock("000FAIL")

        assert result["signal"] == "ERROR"
        assert "현재가 조회 실패" in result["reason"]
        mock_strategy.analyze.assert_not_called() # 전략 분석이 호출되지 않아야 함
        print("analyze_stock (현재가 조회 실패) 테스트 통과")

    def test_scan_stocks(self, mock_kis_client, mock_strategy):
        """scan_stocks 메소드 테스트"""
        service = TradingService(kis_api_client=mock_kis_client, strategy=mock_strategy)
        stock_codes = ["005930", "000660"]
        results = service.scan_stocks(stock_codes)

        assert len(results) == 2
        assert mock_strategy.analyze.call_count == 2
        # The following assertions depend on how mock_strategy.analyze is set up.
        # If it always returns the same stock_code, these will fail for the second call.
        # A side_effect function for the mock is better for distinct return values per call.
        # assert results[0]["stock_code"] == "005930"
        # assert results[1]["stock_code"] == "000660"

        # Using side_effect for more robust testing of scan_stocks
        mock_strategy.analyze.side_effect = lambda sc, df, cp: {
            "stock_code": sc, "signal": "STRATEGY_SIGNAL", "reason": "Dynamic mock",
            "price_at_signal": cp, "current_market_price": cp, "indicators": {}
        }
        results_side_effect = service.scan_stocks(stock_codes)
        assert results_side_effect[0]["stock_code"] == "005930"
        assert results_side_effect[1]["stock_code"] == "000660"
        assert results_side_effect[0]["signal"] == "STRATEGY_SIGNAL"
        print("scan_stocks 테스트 통과")

    def test_execute_order_service_method(self, mock_kis_client):
        """TradingService의 execute_order 메소드 테스트"""
        service = TradingService(kis_api_client=mock_kis_client) # Strategy는 이 메소드와 무관
        result = service.execute_order("005930", "02", 10, 10000.0, "00")

        mock_kis_client.place_order.assert_called_once_with(
            stock_code="005930", order_type="02", quantity=10, price=10000.0, order_condition="00"
        )
        assert result["success"] is True
        assert result["order_id"] == "ORD123"
        print("TradingService.execute_order 테스트 통과")

    def test_get_portfolio_details_service_method(self, mock_kis_client):
        """TradingService의 get_portfolio_details 메소드 테스트"""
        service = TradingService(kis_api_client=mock_kis_client)
        result = service.get_portfolio_details()

        mock_kis_client.get_account_balance.assert_called_once()
        assert result["summary"]["total_cash_balance"] == 1000000.0
        print("TradingService.get_portfolio_details 테스트 통과")

# print("backend/tests/test_trading_service.py 생성 완료") # CLI 명령어 대신 로깅/주석으로 대체
