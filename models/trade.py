from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime

class Stock(BaseModel):
    symbol: str = Field(..., description="주식 심볼 또는 코드, 예: '005930'")
    name: Optional[str] = Field(None, description="주식 이름, 예: '삼성전자'")

class OrderInput(BaseModel):
    stock_symbol: str = Field(..., description="거래할 주식 심볼")
    order_type: str = Field(..., description="주문 유형, 예: 'BUY', 'SELL' (KIS 코드 '01'(매도), '02'(매수)에 매핑될 수 있음)")
    quantity: int = Field(..., gt=0, description="거래할 주식 수량")
    price: Optional[float] = Field(0, description="지정가 주문의 주당 가격. 시장가 주문의 경우 API에 따라 0 또는 None.")
    order_condition: Optional[str] = Field("00", description="주문 조건 코드 (예: KIS API에서 지정가 '00', 시장가 '03'). 기본값은 지정가.")
    # KIS 주문 유형 특정 코드: "01" (매도), "02" (매수)
    # KIS 주문 조건 특정 코드 (주문구분 ORD_DVSN):
    # "00": 지정가
    # "01": 시장가 - 참고: 일부 KIS 문서에는 "01", 다른 문서에는 "03"으로 표기. 확인 필요.
    # "03": 시장가 - TTTC0802U/TTTC0801U (주식현금주문)용
    # "05": 조건부지정가

class OrderOutput(BaseModel):
    order_id: Optional[str] = Field(None, description="증권사 API에서 반환된 주문의 고유 식별자")
    stock_symbol: str
    order_type: str
    quantity: int
    filled_quantity: Optional[int] = Field(None, description="체결된 수량")
    status: str = Field(..., description="주문 상태, 예: 'PENDING'(대기), 'EXECUTED'(체결), 'CANCELLED'(취소), 'FAILED'(실패).")
    message: Optional[str] = Field(None, description="추가 메시지 또는 오류 상세 정보")
    timestamp: datetime = Field(default_factory=datetime.now, description="주문 시간")
    details: Optional[Dict[str, Any]] = Field(None, description="증권사 API의 원시 응답 또는 추가 상세 정보")

class TradingSignal(BaseModel):
    stock_code: str
    timestamp: datetime = Field(default_factory=datetime.now, description="시그널 생성 시점의 타임스탬프 (데이터 포인트 시간)")
    price_at_signal: Optional[float] = Field(None, description="시그널 생성 시점의 주가")
    current_market_price: Optional[float] = Field(None, description="분석 시점의 가장 최근 시장 가격")
    signal: str = Field(..., description="트레이딩 시그널, 예: 'BUY'(매수), 'SELL'(매도), 'HOLD'(보류), 'ERROR'(오류), 'NO_DATA'(데이터 없음), 'NO_INDICATOR'(지표 없음).")
    reason: str = Field(..., description="시그널에 대한 설명")
    indicators: Optional[Dict[str, Optional[float]]] = Field(None, description="시그널 시점의 주요 지표 값, 예: {'bollinger_lower': 100, 'williams_r': -85}")

class PortfolioPosition(BaseModel):
    stock_code: str
    stock_name: Optional[str] = None
    quantity: int
    average_purchase_price: float
    current_price: Optional[float] = None
    eval_amount: Optional[float] = None # 평가금액 (수량 * 현재가)
    profit_loss_amount: Optional[float] = None # 평가손익금액
    profit_loss_ratio: Optional[float] = None # 평가손익률 (%)

class AccountSummary(BaseModel):
    total_cash_balance: Optional[float] = Field(None, description="예수금총금액")
    eval_amount_total: Optional[float] = Field(None, description="총평가금액")
    net_asset_value: Optional[float] = Field(None, description="순자산금액")
    # KIS API output2에서 필요한 경우 다른 요약 필드 추가
    # 예: d2_cash_balance (D+2 예수금), total_purchase_amount (총매입금액)

class Portfolio(BaseModel):
    holdings: List[PortfolioPosition] = []
    summary: Optional[AccountSummary] = None
    timestamp: datetime = Field(default_factory=datetime.now, description="포트폴리오 스냅샷 시간")

class StockScanRequest(BaseModel):
    stock_codes: List[str] = Field(..., min_items=1, description="트레이딩 시그널을 스캔할 주식 코드 목록")

if __name__ == '__main__':
    # 사용 예시
    signal = TradingSignal(
        stock_code="005930",
        price_at_signal=70000.0,
        current_market_price=70100.0,
        signal="BUY",
        reason="가격이 BB하단보다 낮고 WR이 과매도 상태.",
        indicators={"bollinger_lower": 69000.0, "bollinger_upper": 72000.0, "williams_r": -85.0}
    )
    print("트레이딩 시그널 예시:")
    print(signal.model_dump_json(indent=2))

    order_in = OrderInput(
        stock_symbol="005930",
        order_type="BUY", # KIS에서는 "02"로 매핑됨
        quantity=10,
        price=70000.0,
        order_condition="00" # 지정가 주문
    )
    print("\n주문 입력 예시:")
    print(order_in.model_dump_json(indent=2))

    portfolio_pos = PortfolioPosition(
        stock_code="005930",
        stock_name="삼성전자",
        quantity=100,
        average_purchase_price=65000.0,
        current_price=70000.0,
        eval_amount=7000000.0,
        profit_loss_amount=500000.0,
        profit_loss_ratio=7.69
    )
    print("\n포트폴리오 포지션 예시:")
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
    print("\n전체 포트폴리오 예시:")
    print(full_portfolio.model_dump_json(indent=2))
