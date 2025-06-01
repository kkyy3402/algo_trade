from fastapi import FastAPI
from api.trading import router as trading_router
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from scheduler.jobs import scheduled_stock_scan_job # Import your job
import logging

logger = logging.getLogger("main_app")

app = FastAPI(title="Trading Bot API")

# --- Scheduler Setup ---
scheduler = AsyncIOScheduler(timezone="Asia/Seoul") # Or your local timezone

@app.on_event("startup")
async def startup_event():
    logger.info("Application startup: Initializing scheduler...")
    # Add jobs to the scheduler
    # Example: Run 'scheduled_stock_scan_job' every 1 hour
    # For testing, you might use a shorter interval like every 1-5 minutes.
    # Interval can be seconds, minutes, hours, days, weeks.
    # Use cron-style scheduling for more complex timings.
    # scheduler.add_job(scheduled_stock_scan_job, "interval", minutes=5, id="stock_scan_minutely")
    scheduler.add_job(scheduled_stock_scan_job, "interval", hours=1, id="stock_scan_hourly")

    # Start the scheduler
    try:
        scheduler.start()
        logger.info("Scheduler started successfully.")
    except Exception as e:
        logger.error(f"Error starting scheduler: {e}", exc_info=True)
        # Decide if app should fail to start or continue without scheduler

@app.on_event("shutdown")
async def shutdown_event():
    logger.info("Application shutdown: Shutting down scheduler...")
    if scheduler.running:
        scheduler.shutdown(wait=False) # Set wait=True if jobs need to finish gracefully
        logger.info("Scheduler shut down.")

# --- Include API Routers ---
app.include_router(trading_router)

# --- Root Endpoint ---
@app.get("/")
async def root():
    return {"message": "Welcome to the Trading Bot API. Scheduler is active if startup was successful."}

# If you run this file directly with uvicorn:
# if __name__ == "__main__":
#     import uvicorn
#     # Note: Uvicorn's reload feature might cause issues with APScheduler's multiple initializations.
#     # It's often better to run without reload for scheduler stability or handle it carefully.
#     uvicorn.run(app, host="0.0.0.0", port=8000)
