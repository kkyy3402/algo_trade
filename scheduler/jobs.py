import logging
from services.trading_service import TradingService
from services.strategies import TradingStrategy, BollingerWilliamsStrategy # 기본 전략 임포트
from core import kis_api
from core.config import KIS_APP_KEY, KIS_APP_SECRET

logger = logging.getLogger("scheduler_jobs")
# 기본 로깅 설정은 main.py 또는 uvicorn 설정에서 처리하는 것이 일반적입니다.
# 여기서는 스케줄러 작업 전용 로거를 가져와 사용합니다.
# logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')


# --- TradingService 인스턴스 초기화 ---
trading_service_instance = None
if not KIS_APP_KEY or not KIS_APP_SECRET: # KIS API 키/비밀키가 없는 경우
    logger.warning("KIS API 키/비밀키 미설정. 스케줄링된 작업이 KIS API 호출 시 실패할 수 있습니다.")
else:
    try:
        default_strategy_for_scheduler = BollingerWilliamsStrategy()
        trading_service_instance = TradingService(
            kis_api_client=kis_api,
            strategy=default_strategy_for_scheduler
        )
        logger.info(f"스케줄러용 TradingService 초기화 완료 (전략: {default_strategy_for_scheduler.__class__.__name__})")
    except Exception as e:
        logger.error(f"스케줄러용 TradingService 초기화 실패: {e}", exc_info=True)


# --- 스케줄링된 작업 정의 ---
def scheduled_stock_scan_job():
    """
    사전 정의된 주식 목록을 주기적으로 스캔하고 시그널을 로깅합니다.
    """
    if not trading_service_instance:
        logger.error("TradingService 미초기화 (KIS 설정 누락 가능성). 스케줄링된 스캔을 건너뜁니다.")
        return

    # TODO: 모니터링할 주식 목록은 설정 파일, DB 등에서 가져오도록 개선이 필요합니다.
    stocks_to_monitor = ["005930", "035720", "000660"] # 예: 삼성전자, 카카오, SK하이닉스

    logger.info(f"스케줄러: 다음 주식에 대한 스캔을 시작합니다: {stocks_to_monitor}")

    try:
        scan_results = trading_service_instance.scan_stocks(stocks_to_monitor)
        logger.info("스케줄러: 스캔 결과:")
        for result in scan_results:
            logger.info(
                f"  종목: {result.get('stock_code')}, "
                f"시그널: {result.get('signal')}, "
                f"시그널 시점 가격: {result.get('price_at_signal')}, "
                f"이유: {result.get('reason')}"
            )
            # TODO: 시그널 기반 추가 작업 구현 (예: DB 저장, 알림 발송, 자동 거래 등)
            # (자동 거래는 리스크 관리, 포지션 추적 등 신중한 구현이 필요합니다)

    except Exception as e:
        logger.error(f"스케줄러: 주식 스캔 중 오류가 발생했습니다: {e}", exc_info=True)

if __name__ == '__main__':
    # 이 파일을 직접 실행하여 작업 함수를 테스트합니다.
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    logger.info("scheduled_stock_scan_job 수동 테스트를 시작합니다...")

    if not trading_service_instance :
        logger.warning("실제 TradingService 초기화 실패. Mock 서비스로 테스트 시도 (KIS API 호출 없음).")
        # strategies.py의 TradingStrategy 임포트가 필요합니다. (이미 상단에 있음)
        class MockStrategy(TradingStrategy):
            def analyze(self, stock_code: str, data: pd.DataFrame, current_price: float) -> dict:
                return {"stock_code": stock_code, "signal": "HOLD", "reason": "Mocked signal", "price_at_signal": 100.0, "current_market_price": 100.0, "indicators": {}}

        class MockTradingService:
            def __init__(self, strategy): self.strategy = strategy
            def scan_stocks(self, stock_codes: list):
                logger.info(f"[MockTradingService] 주식 스캔: {stock_codes} (전략: {self.strategy.__class__.__name__})")
                return [self.strategy.analyze(code, pd.DataFrame(), 0.0) for code in stock_codes] # 빈 DataFrame 전달

        trading_service_instance = MockTradingService(strategy=MockStrategy())

    scheduled_stock_scan_job()
    logger.info("수동 작업 테스트가 완료되었습니다.")
