import pytest
from fastapi.testclient import TestClient
from unittest.mock import MagicMock, patch

# main:app을 임포트하기 전에, 테스트 환경에 맞는 의존성 mock 설정이 필요할 수 있음
# 예를 들어, KIS API 키가 없어도 앱이 로드될 수 있도록 config 등을 mock
# 지금은 get_trading_service를 mock하여 TradingService 자체를 대체하므로 괜찮을 수 있음

from main import app # FastAPI app instance
from services.trading_service import TradingService # To mock its methods or use as type hint
from models.trade import TradingSignal, OrderOutput, Portfolio # For response validation if needed

@pytest.fixture
def client():
    """FastAPI TestClient 인스턴스 생성"""
    return TestClient(app)

@pytest.fixture
def mock_trading_service():
    """TradingService의 mock 인스턴스 생성"""
    service_mock = MagicMock(spec=TradingService)
    service_mock.scan_stocks.return_value = [
        TradingSignal(stock_code="005930", signal="BUY", reason="Mocked API BUY", price_at_signal=70000.0, current_market_price=70000.0, indicators={}).model_dump()
    ]
    # Ensure execute_order returns a dict that OrderOutput can parse
    service_mock.execute_order.return_value = {"success": True, "order_id": "API_ORD123", "details": {"msg": "API mock success"}}
    # Ensure get_portfolio_details returns a dict that Portfolio can parse
    service_mock.get_portfolio_details.return_value = {"holdings": [], "summary": {"total_cash_balance": 2000000.0}}
    return service_mock

# FastAPI의 Depends를 사용하는 get_trading_service 함수를 패치하여 mock_trading_service를 반환하도록 함
# 이렇게 하면 API 엔드포인트가 실제 TradingService 대신 mock 객체를 사용하게 됨
@pytest.fixture(autouse=True) # 모든 테스트에 자동 적용
def override_get_trading_service(mock_trading_service: MagicMock):
    # api.trading 모듈 내의 get_trading_service를 mock_trading_service_dependency 함수로 대체
    # 이 mock_trading_service_dependency 함수는 우리가 만든 mock_trading_service 인스턴스를 반환함
    def mock_trading_service_dependency():
        return mock_trading_service

    # app.dependency_overrides를 사용하여 의존성 주입을 오버라이드
    # api.trading.get_trading_service 경로가 실제 프로젝트 구조와 일치해야 함
    # main.py에서 from api.trading import get_trading_service 하는 경우라면 이 방식이 맞음. (현재 구조)
    from api.trading import get_trading_service as actual_get_trading_service
    app.dependency_overrides[actual_get_trading_service] = mock_trading_service_dependency
    yield # 테스트 실행 동안 패치가 활성화됨
    app.dependency_overrides.clear() # 테스트 후 오버라이드 클리어


class TestTradingAPI:
    def test_scan_stocks_api(self, client: TestClient, mock_trading_service: MagicMock):
        """POST /api/scan_stocks 엔드포인트 테스트"""
        response = client.post("/api/scan_stocks", json={"stock_codes": ["005930"]})

        assert response.status_code == 200
        json_response = response.json()
        assert len(json_response) == 1
        assert json_response[0]["stock_code"] == "005930"
        assert json_response[0]["signal"] == "BUY"
        mock_trading_service.scan_stocks.assert_called_once_with(stock_codes=["005930"])
        # print("POST /api/scan_stocks 테스트 통과") # pytest에서는 print 대신 logging 또는 assert로 결과 확인

    def test_execute_trade_api(self, client: TestClient, mock_trading_service: MagicMock):
        """POST /api/execute_trade 엔드포인트 테스트"""
        order_data = {
            "stock_symbol": "005930", "order_type": "02", # BUY
            "quantity": 10, "price": 70000.0, "order_condition": "00" # Limit
        }
        response = client.post("/api/execute_trade", json=order_data)

        assert response.status_code == 200 # 성공/실패 모두 200으로 처리하고 내부 status로 구분 (API 설계에 따름)
        json_response = response.json()

        # OrderOutput 모델에 따라 필드 확인
        assert json_response["order_id"] == "API_ORD123"
        assert json_response["status"] == "PENDING" # execute_trade_endpoint의 성공 로직에 따름
        assert json_response["stock_symbol"] == order_data["stock_symbol"]

        mock_trading_service.execute_order.assert_called_once_with(
            stock_code="005930", order_type="02", quantity=10, price=70000.0, order_condition="00"
        )
        # print("POST /api/execute_trade 테스트 통과")

    def test_get_portfolio_api(self, client: TestClient, mock_trading_service: MagicMock):
        """GET /api/portfolio 엔드포인트 테스트"""
        response = client.get("/api/portfolio")

        assert response.status_code == 200
        json_response = response.json()
        assert json_response["summary"]["total_cash_balance"] == 2000000.0
        mock_trading_service.get_portfolio_details.assert_called_once()
        # print("GET /api/portfolio 테스트 통과")

    def test_trade_history_api_placeholder(self, client: TestClient):
        """GET /api/trade_history (플레이스홀더) 엔드포인트 테스트"""
        response = client.get("/api/trade_history")
        assert response.status_code == 200 # 현재 빈 리스트 반환
        assert response.json() == []
        # print("GET /api/trade_history (플레이스홀더) 테스트 통과")

# print("backend/tests/test_api_trading.py 생성 완료") # CLI 명령어 대신 로깅/주석으로 대체
