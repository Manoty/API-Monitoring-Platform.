from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.core.logging import setup_logging, get_logger
from app.core.database import init_db, close_db
from app.api import api_router
from app.workers import start_scheduler, stop_scheduler
from app.workers.retention import purge_old_checks
from apscheduler.triggers.cron import CronTrigger
from app.workers.scheduler import scheduler

setup_logging()
logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown logic."""
    logger.info(f"Starting {settings.APP_NAME} v{settings.VERSION}")

    # boot DB (dev only — prod uses alembic)
    await init_db()

    # start the monitoring scheduler + load all endpoints
    await start_scheduler()

    # daily retention purge job — runs at 2am every day
    scheduler.add_job(
        purge_old_checks,
        trigger=CronTrigger(hour=2, minute=0),
        id="retention_purge",
        replace_existing=True,
    )

    logger.info("All systems up")
    yield

    # shutdown
    logger.info("Shutting down...")
    await stop_scheduler()
    await close_db()
    logger.info("Shutdown complete")


app = FastAPI(
    title=settings.APP_NAME,
    version=settings.VERSION,
    debug=settings.DEBUG,
    lifespan=lifespan,
)

# CORS — tighten in production
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# mount all routes under /api/v1
app.include_router(api_router, prefix="/api/v1")


@app.get("/health", tags=["Health"])
async def health_check():
    """Quick liveness probe for Docker/load balancers."""
    return {"status": "ok", "version": settings.VERSION}