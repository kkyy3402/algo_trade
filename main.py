from fastapi import FastAPI
from api.trading import router as trading_router
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from scheduler.jobs import scheduled_stock_scan_job # 작업 임포트
import logging

logger = logging.getLogger("main_app")

app = FastAPI(title="트레이딩 봇 API")

# --- 스케줄러 설정 ---
scheduler = AsyncIOScheduler(timezone="Asia/Seoul") # 또는 현재 지역 시간대

@app.on_event("startup")
async def startup_event():
    logger.info("애플리케이션 시작: 스케줄러 초기화 중...")
    # 스케줄러에 작업 추가
    # 예: 매 1시간마다 'scheduled_stock_scan_job' 실행
    # 테스트 시에는 1-5분과 같이 짧은 간격 사용 가능.
    # 간격은 초, 분, 시간, 일, 주 단위로 설정 가능.
    # 더 복잡한 시간 설정은 cron 스타일 스케줄링 사용.
    # scheduler.add_job(scheduled_stock_scan_job, "interval", minutes=5, id="stock_scan_minutely")
    scheduler.add_job(scheduled_stock_scan_job, "interval", hours=1, id="stock_scan_hourly")

    # 스케줄러 시작
    try:
        scheduler.start()
        logger.info("스케줄러가 성공적으로 시작되었습니다.")
    except Exception as e:
        logger.error(f"스케줄러 시작 중 오류 발생: {e}", exc_info=True)
        # 앱 시작 실패 또는 스케줄러 없이 계속할지 결정

@app.on_event("shutdown")
async def shutdown_event():
    logger.info("애플리케이션 종료: 스케줄러 종료 중...")
    if scheduler.running:
        scheduler.shutdown(wait=False) # 작업이 정상적으로 완료되어야 한다면 wait=True 설정
        logger.info("스케줄러가 종료되었습니다.")

# --- API 라우터 포함 ---
app.include_router(trading_router)

# --- 루트 엔드포인트 ---
@app.get("/")
async def root():
    return {"message": "트레이딩 봇 API에 오신 것을 환영합니다. 시작 시 스케줄러가 성공적으로 활성화되었습니다."}

# uvicorn으로 이 파일을 직접 실행하는 경우:
# if __name__ == "__main__":
#     import uvicorn
#     # 참고: Uvicorn의 reload 기능은 APScheduler의 다중 초기화 문제를 일으킬 수 있음.
#     # 스케줄러 안정성을 위해 reload 없이 실행하거나 신중하게 처리하는 것이 좋음.
#     uvicorn.run(app, host="0.0.0.0", port=8000)
