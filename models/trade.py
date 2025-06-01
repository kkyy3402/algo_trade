from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime

class Stock(BaseModel):
    symbol: str = Field(..., description="Stock symbol or code, e.g., '005930'")
    name: Optional[str] = Field(None, description="Name of the stock, e.g., 'Samsung Electronics'")

class OrderInput(BaseModel):
    stock_symbol: str = Field(..., description="Stock symbol to trade")
    order_type: str = Field(..., description="Type of order, e.g., 'BUY', 'SELL' (these might map to KIS codes like '01' for sell, '02' for buy)")
    quantity: int = Field(..., gt=0, description="Number of shares to trade")
    price: Optional[float] = Field(0, description="Price per share for limit orders. 0 or None for market orders, depending on API.")
    order_condition: Optional[str] = Field("00", description="Order condition code (e.g., '00' for Limit, '03' for Market in KIS API). Defaults to Limit.")
    # KIS specific codes for order_type: "01" (매도, Sell), "02" (매수, Buy)
    # KIS specific codes for order_condition (주문구분 ORD_DVSN):
    # "00": 지정가 (Limit Order)
    # "01": 시장가 (Market Order) - Note: Some KIS docs say "01", others "03". Needs verification.
    # "03": 시장가 (Market Order) - For TTTC0802U/TTTC0801U (주식현금주문)
    # "05": 조건부지정가 (Conditional Limit Order)

class OrderOutput(BaseModel):
    order_id: Optional[str] = Field(None, description="Unique identifier for the order returned by the brokerage API")
    stock_symbol: str
    order_type: str
    quantity: int
    filled_quantity: Optional[int] = Field(None)
    status: str = Field(..., description="Status of the order, e.g., 'PENDING', 'EXECUTED', 'CANCELLED', 'FAILED'")
    message: Optional[str] = Field(None, description="Additional message or error details")
    timestamp: datetime = Field(default_factory=datetime.now)
    details: Optional[Dict[str, Any]] = Field(None, description="Raw response or additional details from the brokerage API")

class TradingSignal(BaseModel):
    stock_code: str
    timestamp: datetime = Field(default_factory=datetime.now, description="Timestamp of when the signal was generated (data point time)")
    price_at_signal: Optional[float] = Field(None, description="Price of the stock when the signal was generated")
    current_market_price: Optional[float] = Field(None, description="Most recent market price available at time of analysis")
    signal: str = Field(..., description="Trading signal, e.g., 'BUY', 'SELL', 'HOLD', 'ERROR', 'NO_DATA', 'NO_INDICATOR'")
    reason: str = Field(..., description="Explanation for the signal")
    indicators: Optional[Dict[str, Optional[float]]] = Field(None, description="Key indicator values at the time of signal, e.g., {'bollinger_lower': 100, 'williams_r': -85}")

class PortfolioPosition(BaseModel):
    stock_code: str
    stock_name: Optional[str] = None
    quantity: int
    average_purchase_price: float
    current_price: Optional[float] = None
    eval_amount: Optional[float] = None # 평가금액 (quantity * current_price)
    profit_loss_amount: Optional[float] = None # 평가손익금액
    profit_loss_ratio: Optional[float] = None # 평가손익률 (%)

class AccountSummary(BaseModel):
    total_cash_balance: Optional[float] = Field(None, description="예수금총금액 (Total cash available)")
    eval_amount_total: Optional[float] = Field(None, description="총평가금액 (Total evaluation amount of all assets)")
    net_asset_value: Optional[float] = Field(None, description="순자산금액 (Net asset value)")
    # Add other summary fields from KIS API output2 if needed
    # e.g., d2_cash_balance (D+2 예수금), total_purchase_amount (총매입금액)

class Portfolio(BaseModel):
    holdings: List[PortfolioPosition] = []
    summary: Optional[AccountSummary] = None
    timestamp: datetime = Field(default_factory=datetime.now)

class StockScanRequest(BaseModel):
    stock_codes: List[str] = Field(..., min_items=1, description="List of stock codes to scan for trading signals")

if __name__ == '__main__':
    # Example Usage
    signal = TradingSignal(
        stock_code="005930",
        price_at_signal=70000.0,
        current_market_price=70100.0,
        signal="BUY",
        reason="Price below lower BB and WR oversold.",
        indicators={"bollinger_lower": 69000.0, "bollinger_upper": 72000.0, "williams_r": -85.0}
    )
    print("Trading Signal Example:")
    print(signal.model_dump_json(indent=2))

    order_in = OrderInput(
        stock_symbol="005930",
        order_type="BUY", # This would map to "02" for KIS
        quantity=10,
        price=70000.0,
        order_condition="00" # Limit order
    )
    print("\nOrder Input Example:")
    print(order_in.model_dump_json(indent=2))

    portfolio_pos = PortfolioPosition(
        stock_code="005930",
        stock_name="Samsung Electronics",
        quantity=100,
        average_purchase_price=65000.0,
        current_price=70000.0,
        eval_amount=7000000.0,
        profit_loss_amount=500000.0,
        profit_loss_ratio=7.69
    )
    print("\nPortfolio Position Example:")
    print(portfolio_pos.model_dump_json(indent=2))

    account_sum = AccountSummary(
        total_cash_balance=10000000.0,
        eval_amount_total=25000000.0,
        net_asset_value=35000000.0
    )
    full_portfolio = Portfolio(
        holdings=[portfolio_pos],
        summary=account_sum
    )
    print("\nFull Portfolio Example:")
    print(full_portfolio.model_dump_json(indent=2))
