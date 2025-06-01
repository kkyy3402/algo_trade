from fastapi import APIRouter, HTTPException, Depends, Body
from typing import List

from models.trade import StockScanRequest, TradingSignal, OrderInput, OrderOutput, Portfolio
from services.trading_service import TradingService
from core import kis_api
from core.config import KIS_APP_KEY, KIS_APP_SECRET
from services.strategies import BollingerWilliamsStrategy # 기본 전략 임포트

import logging

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/api",
    tags=["Trading"], # Swagger UI 그룹화 태그
)

def get_trading_service():
    if not KIS_APP_KEY or not KIS_APP_SECRET:
        logger.warning("KIS API 키/비밀키 미설정. Trading Service 기능이 제한될 수 있습니다.")
        # 프로덕션 환경에서는 여기서 HTTPException을 발생시키거나, 서비스가 KIS API 호출 시 실패하도록 처리할 수 있습니다.

    # 기본 전략(BollingerWilliamsStrategy)으로 TradingService 인스턴스를 생성합니다.
    # 추후에는 설정 파일이나 요청 파라미터를 통해 다른 전략을 선택할 수 있도록 확장할 수 있습니다.
    default_strategy = BollingerWilliamsStrategy()
    service_instance = TradingService(kis_api_client=kis_api, strategy=default_strategy)
    return service_instance


@router.post("/scan_stocks", response_model=List[TradingSignal])
async def scan_stocks_endpoint(
    scan_request: StockScanRequest,
    trading_service: TradingService = Depends(get_trading_service)
):
    """
    볼린저 밴드와 Williams %R을 기반으로 여러 주식의 트레이딩 시그널을 분석합니다.
    (현재는 기본 전략으로 고정되어 있습니다.)
    """
    try:
        logger.info(f"API: 주식 스캔 요청 수신: {scan_request.stock_codes}")
        results = trading_service.scan_stocks(stock_codes=scan_request.stock_codes)
        return results
    except Exception as e:
        logger.error(f"API 오류 /scan_stocks: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"주식 스캔에 실패했습니다: {str(e)}")

@router.post("/execute_trade", response_model=OrderOutput)
async def execute_trade_endpoint(
    order_input: OrderInput,
    trading_service: TradingService = Depends(get_trading_service)
):
    """
    지정된 주식에 대해 거래 주문(매수/매도)을 실행합니다.

    **참고:** KIS API는 'order_type' 및 'order_condition'에 특정 코드가 필요합니다.
    - 'order_type': "01" (매도), "02" (매수).
    - 'order_condition': 예: "00" (지정가), "03" (시장가).
      올바른 코드는 'OrderInput' 모델 및 KIS 문서를 참조하십시오.
    """
    logger.info(f"API: 거래 실행 요청 수신: {order_input.model_dump_json(exclude_none=True)}")

    try:
        api_response = trading_service.execute_order(
            stock_code=order_input.stock_symbol,
            order_type=order_input.order_type,
            quantity=order_input.quantity,
            price=order_input.price, # TradingService.execute_order는 price를 필수 인자로 받습니다.
            order_condition=order_input.order_condition
        )

        if api_response.get("success"):
            return OrderOutput(
                order_id=api_response.get("order_id"),
                stock_symbol=order_input.stock_symbol,
                order_type=order_input.order_type,
                quantity=order_input.quantity,
                status="PENDING" if api_response.get("order_id") else "SUBMITTED_NO_ID",
                message="주문이 성공적으로 제출되었습니다.",
                details=api_response.get("details")
            )
        else:
            error_msg = api_response.get("error", "거래 실행 중 알 수 없는 오류가 발생했습니다.")
            logger.error(f"API 오류 /execute_trade - KIS API 실패 보고: {error_msg}")
            return OrderOutput(
                stock_symbol=order_input.stock_symbol,
                order_type=order_input.order_type,
                quantity=order_input.quantity,
                status="FAILED",
                message=error_msg,
                details=api_response.get("details")
            )
    except Exception as e:
        logger.error(f"API 오류 /execute_trade: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"거래 실행에 실패했습니다: {str(e)}")

@router.get("/portfolio", response_model=Portfolio)
async def get_portfolio_endpoint(
    trading_service: TradingService = Depends(get_trading_service)
):
    """
    현재 포트폴리오 보유 현황 및 계좌 잔고를 조회합니다.
    """
    logger.info("API: 포트폴리오 조회 요청 수신.")
    try:
        account_data = trading_service.get_portfolio_details()

        if "error" in account_data and account_data.get("error"): # error 필드가 존재하고, 내용도 있을 경우
            logger.error(f"API 오류 /portfolio - KIS API 실패 보고: {account_data['error']}")
            raise HTTPException(status_code=500, detail=f"포트폴리오 조회에 실패했습니다: {account_data['error']}")

        return Portfolio(
            holdings=[PortfolioPosition(**h) for h in account_data.get("holdings", [])],
            summary=AccountSummary(**account_data.get("summary", {})) if account_data.get("summary") else None
        )
    except Exception as e:
        logger.error(f"API 오류 /portfolio: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"포트폴리오 조회에 실패했습니다: {str(e)}")

@router.get("/trade_history", response_model=List[OrderOutput])
async def get_trade_history_endpoint():
    """
    (플레이스홀더) 실행된 거래 내역을 조회합니다.
    이 엔드포인트는 거래 내역을 가져오기 위한 KIS API 함수 구현 및 해당 데이터를 OrderOutput 모델 목록에 매핑하는 작업이 필요합니다.
    """
    logger.info("API: 거래 내역 조회 요청 수신 (플레이스홀더).")
    return []

logger.info("트레이딩 API 라우터 생성 완료: /scan_stocks, /execute_trade, /portfolio, /trade_history 엔드포인트를 포함합니다.")
