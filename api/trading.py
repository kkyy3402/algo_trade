from fastapi import APIRouter, HTTPException, Depends, Body
from typing import List

from models.trade import StockScanRequest, TradingSignal, OrderInput, OrderOutput, Portfolio
from services.trading_service import TradingService
# Assuming kis_api module is accessible for direct calls if needed, or TradingService handles all.
from core import kis_api
from core.config import KIS_APP_KEY, KIS_APP_SECRET # For dependency checking or direct use if necessary

import logging

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/api",
    tags=["Trading"], # Tag for Swagger UI grouping
)

# --- Dependency Injection for TradingService ---
# This makes it easier to manage the service instance and its dependencies (like KIS API client)
# For now, TradingService instantiates its own KIS client or uses the global one.
# A more advanced setup might inject a configured KIS client into TradingService.
def get_trading_service():
    # Check if KIS API is configured (basic check)
    if not KIS_APP_KEY or not KIS_APP_SECRET:
        # This check could be more sophisticated, e.g. trying to get a token
        logger.error("KIS API Key/Secret not configured. Trading Service may not function.")
        # Depending on policy, you could raise HTTPException here or let service fail.
    # Pass the actual KIS API module to the service.
    # The TradingService is designed to use the imported kis_api by default.
    return TradingService(kis_api_client=kis_api)


@router.post("/scan_stocks", response_model=List[TradingSignal])
async def scan_stocks_endpoint(
    scan_request: StockScanRequest,
    trading_service: TradingService = Depends(get_trading_service)
):
    """
    Analyzes a list of stocks for trading signals based on Bollinger Bands and Williams %R.
    """
    try:
        logger.info(f"API: Received request to scan stocks: {scan_request.stock_codes}")
        # The TradingService's scan_stocks method is expected to return a list of dicts
        # that are compatible with the TradingSignal Pydantic model.
        results = trading_service.scan_stocks(stock_codes=scan_request.stock_codes)

        # Convert results to TradingSignal objects for response validation
        # Pydantic will automatically try to parse the dicts into TradingSignal models.
        # If a dict doesn't match, it will raise a validation error handled by FastAPI.
        return results
    except Exception as e:
        logger.error(f"API Error during /scan_stocks: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to scan stocks: {str(e)}")

@router.post("/execute_trade", response_model=OrderOutput)
async def execute_trade_endpoint(
    order_input: OrderInput,
    trading_service: TradingService = Depends(get_trading_service) # Or directly use kis_api
):
    """
    Places a trade order (buy/sell) for a given stock.

    **Note:** KIS API requires specific codes for `order_type` and `order_condition`.
    - `order_type`: "01" for Sell, "02" for Buy.
    - `order_condition`: e.g., "00" for Limit Order, "03" for Market Order.
      Refer to `OrderInput` model and KIS documentation for correct codes.
    """
    logger.info(f"API: Received request to execute trade: {order_input.model_dump_json()}")

    # Basic validation or mapping if frontend sends "BUY"/"SELL"
    # For now, assume client sends KIS-compatible codes or OrderInput model handles it.

    try:
        # The kis_api.place_order function is expected to return a dict.
        # This dict should be structured to match OrderOutput Pydantic model.
        # Example: {"success": True, "order_id": "12345", "details": {...}}
        # We need to map this to OrderOutput structure.

        # Using the new TradingService method
        api_response = trading_service.execute_order(
            stock_code=order_input.stock_symbol,
            order_type=order_input.order_type,
            quantity=order_input.quantity,
            price=order_input.price,  # OrderInput.price defaults to 0.0 if not provided
            order_condition=order_input.order_condition
        )

        if api_response.get("success"):
            return OrderOutput(
                order_id=api_response.get("order_id"),
                stock_symbol=order_input.stock_symbol,
                order_type=order_input.order_type, # Store what was requested
                quantity=order_input.quantity,
                status="PENDING" if api_response.get("order_id") else "SUBMITTED_NO_ID", # Or more specific status from API
                message="Order submitted successfully.",
                details=api_response.get("details")
            )
        else:
            error_msg = api_response.get("error", "Unknown error during trade execution.")
            logger.error(f"API Error during /execute_trade - KIS API reported failure: {error_msg}")
            # Return a valid OrderOutput with error status
            return OrderOutput(
                stock_symbol=order_input.stock_symbol,
                order_type=order_input.order_type,
                quantity=order_input.quantity,
                status="FAILED",
                message=error_msg,
                details=api_response.get("details") # Include if any error details are present
            )
            # Or raise HTTPException:
            # raise HTTPException(status_code=400, detail=f"Trade execution failed: {error_msg}")

    except Exception as e:
        logger.error(f"API Error during /execute_trade: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to execute trade: {str(e)}")

@router.get("/portfolio", response_model=Portfolio)
async def get_portfolio_endpoint(
    trading_service: TradingService = Depends(get_trading_service) # Or directly use kis_api
):
    """
    Retrieves the current portfolio holdings and account balance.
    """
    logger.info("API: Received request to get portfolio.")
    try:
        # Using the new TradingService method
        account_data = trading_service.get_portfolio_details()

        if "error" in account_data:
            logger.error(f"API Error during /portfolio - KIS API reported failure: {account_data['error']}")
            raise HTTPException(status_code=500, detail=f"Failed to fetch portfolio: {account_data['error']}")

        # Transform data from KIS API format to Portfolio Pydantic model
        # kis_api.get_account_balance() returns: {"holdings": [...], "summary": {...}}
        # 'holdings' items match PortfolioPosition fields fairly well.
        # 'summary' items match AccountSummary fields.

        return Portfolio(
            holdings=[PortfolioPosition(**h) for h in account_data.get("holdings", [])],
            summary=AccountSummary(**account_data.get("summary", {})) if account_data.get("summary") else None
        )
    except Exception as e:
        logger.error(f"API Error during /portfolio: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to retrieve portfolio: {str(e)}")

@router.get("/trade_history", response_model=List[OrderOutput])
async def get_trade_history_endpoint(
    # trading_service: TradingService = Depends(get_trading_service) # Or directly use kis_api
):
    """
    (Placeholder) Retrieves the history of executed trades.
    This endpoint requires implementation of a KIS API function to fetch trade history
    and then mapping that data to a list of OrderOutput models.
    """
    logger.info("API: Received request to get trade history (placeholder).")
    # TODO: Implement logic to fetch trade history from KIS API.
    # This would involve:
    # 1. Adding a function like `get_order_history()` to `core/kis_api.py`.
    #    - This function would call the relevant KIS API endpoint (e.g., "일별 주문 체결 조회" - TTTC8001R).
    #    - It would parse the response which typically includes details of filled/partially_filled/cancelled orders.
    # 2. Calling that function here.
    # 3. Transforming the KIS API response into a list of `OrderOutput` Pydantic models.
    #    - Each item in the list would represent a past trade with its status, filled quantity, price, etc.

    # For now, returning an empty list as a placeholder.
    # raise HTTPException(status_code=501, detail="Trade history endpoint is not yet implemented.")
    return []

# Example of how to add more specific endpoints if needed:
# @router.get("/stocks/{stock_symbol}/price", response_model=StockPrice) # Define StockPrice model
# async def get_stock_price_endpoint(stock_symbol: str, trading_service: TradingService = Depends(get_trading_service)):
#     price = trading_service.kis_client.get_stock_price(stock_symbol)
#     if price is None:
#         raise HTTPException(status_code=404, detail="Stock price not found.")
#     return {"symbol": stock_symbol, "price": price, "timestamp": datetime.now()}

logger.info("Trading API router created with /scan_stocks, /execute_trade, /portfolio, /trade_history endpoints.")
