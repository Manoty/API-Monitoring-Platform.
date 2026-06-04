import asyncio
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger
from sqlalchemy import select

from app.core.database import AsyncSessionFactory
from app.core.logging import get_logger
from app.models.endpoint import Endpoint, EndpointStatus
from app.workers.monitor import ping_endpoint

logger = get_logger(__name__)

# one global scheduler instance
scheduler = AsyncIOScheduler()


async def run_check_for_endpoint(endpoint_id: str) -> None:
    """Fetches the endpoint from DB and runs a ping. Each job calls this."""
    async with AsyncSessionFactory() as db:
        try:
            result = await db.execute(
                select(Endpoint).where(Endpoint.id == endpoint_id)
            )
            endpoint = result.scalar_one_or_none()

            if not endpoint:
                logger.warning(f"Scheduled job: endpoint {endpoint_id} not found, removing job")
                scheduler.remove_job(job_id=str(endpoint_id))
                return

            if endpoint.status == EndpointStatus.PAUSED:
                logger.debug(f"Skipping paused endpoint: {endpoint.name}")
                return

            logger.info(f"Running check | endpoint={endpoint.name} | url={endpoint.url}")
            await ping_endpoint(endpoint, db)
            await db.commit()

        except Exception as e:
            logger.error(f"Check failed unexpectedly for {endpoint_id}: {e}", exc_info=True)
            await db.rollback()


def schedule_endpoint(endpoint: Endpoint) -> None:
    """Add or replace a job for this endpoint in the scheduler."""
    job_id = str(endpoint.id)

    # remove existing job if interval changed
    if scheduler.get_job(job_id):
        scheduler.remove_job(job_id)

    scheduler.add_job(
        run_check_for_endpoint,
        trigger=IntervalTrigger(seconds=endpoint.interval_seconds),
        id=job_id,
        args=[str(endpoint.id)],
        max_instances=1,          # never run two checks for same endpoint simultaneously
        coalesce=True,            # if a job is missed, run it once not many times
        replace_existing=True,
    )
    logger.info(f"Scheduled | endpoint={endpoint.name} | every {endpoint.interval_seconds}s")


def unschedule_endpoint(endpoint_id: str) -> None:
    """Remove a job when endpoint is deleted or paused."""
    if scheduler.get_job(endpoint_id):
        scheduler.remove_job(endpoint_id)
        logger.info(f"Unscheduled endpoint {endpoint_id}")


async def load_all_endpoints() -> None:
    """On startup — load all active endpoints and schedule them."""
    async with AsyncSessionFactory() as db:
        result = await db.execute(
            select(Endpoint).where(Endpoint.status != EndpointStatus.PAUSED)
        )
        endpoints = result.scalars().all()

    for endpoint in endpoints:
        schedule_endpoint(endpoint)

    logger.info(f"Loaded {len(endpoints)} endpoints into scheduler")


async def start_scheduler() -> None:
    await load_all_endpoints()
    scheduler.start()
    logger.info("Scheduler started")


async def stop_scheduler() -> None:
    scheduler.shutdown(wait=False)
    logger.info("Scheduler stopped")