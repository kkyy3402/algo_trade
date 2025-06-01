import logging
from services.trading_service import TradingService
from core import kis_api # TradingService might need this explicitly or it's handled internally
from core.config import KIS_APP_KEY, KIS_APP_SECRET

# Configure logging for scheduler jobs
logger = logging.getLogger("scheduler_jobs")
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

# --- Initialize Trading Service ---
# Ensure KIS API keys are loaded for the service
if not KIS_APP_KEY or not KIS_APP_SECRET:
    logger.warning("KIS API Key/Secret not configured. Scheduled jobs requiring API access may fail.")
    # Potentially raise an error or prevent job scheduling if critical
    trading_service_instance = None # Or a mock/dummy service
else:
    # Assuming TradingService can be instantiated like this.
    # If it needs a KIS client instance directly, that needs to be passed.
    # The current TradingService uses the global kis_api module by default.
    trading_service_instance = TradingService(kis_api_client=kis_api)

# --- Scheduled Job Definitions ---
def scheduled_stock_scan_job():
    """
    Periodically scans a predefined list of stocks and logs the signals.
    """
    if not trading_service_instance:
        logger.error("TradingService not initialized due to missing KIS configuration. Skipping scheduled scan.")
        return

    # TODO: Stock list should be configurable (e.g., from .env, a config file, or database)
    stocks_to_monitor = ["005930", "035720", "000660"] # Example: Samsung, Kakao, SK Hynix

    logger.info(f"Scheduler: Starting scheduled scan for stocks: {stocks_to_monitor}")

    try:
        scan_results = trading_service_instance.scan_stocks(stocks_to_monitor)
        logger.info("Scheduler: Scan Results:")
        for result in scan_results:
            logger.info(
                f"  Stock: {result.get('stock_code')}, "
                f"Signal: {result.get('signal')}, "
                f"PriceAtSignal: {result.get('price_at_signal')}, "
                f"Reason: {result.get('reason')}"
            )
            # TODO: Implement further actions based on signals, e.g.,
            # - Store signals in a database.
            # - Send notifications.
            # - If auto-trading is enabled and conditions are met, place trades.
            #   (This requires careful implementation of trade execution logic,
            #    risk management, and position tracking).

    except Exception as e:
        logger.error(f"Scheduler: Error during scheduled stock scan: {e}", exc_info=True)

if __name__ == '__main__':
    # For testing the job function directly
    logger.info("Testing scheduled_stock_scan_job manually...")
    # This direct call will use the live KIS API if configured and TradingService is set up for it.
    # Or the mock if TradingService's KIS client is mocked by default.
    # For true testing, one might mock TradingService.scan_stocks here.

    # To test with a mock service if KIS keys are not set:
    class MockTradingService:
        def scan_stocks(self, stock_codes: list):
            logger.info(f"[MockTradingService] Scanning stocks: {stock_codes}")
            return [
                {"stock_code": code, "signal": "HOLD", "price_at_signal": 100.0, "reason": "Mocked signal"}
                for code in stock_codes
            ]

    if not trading_service_instance: # If real service failed to init due to no keys
        logger.info("Using MockTradingService for manual job test as KIS keys are likely missing.")
        trading_service_instance = MockTradingService() # Temporarily override for test

    scheduled_stock_scan_job()
    logger.info("Manual job test finished.")
