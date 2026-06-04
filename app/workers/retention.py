from datetime import datetime, timedelta
from sqlalchemy import delete

from app.core.database import AsyncSessionFactory
from app.core.config import settings
from app.core.logging import get_logger
from app.models.check import Check

logger = get_logger(__name__)


async def purge_old_checks() -> None:
    """
    Delete check records older than METRIC_RETENTION_DAYS.
    Runs once daily via scheduler. Keeps the checks table lean.
    """
    cutoff = datetime.utcnow() - timedelta(days=settings.METRIC_RETENTION_DAYS)

    async with AsyncSessionFactory() as db:
        try:
            result = await db.execute(
                delete(Check).where(Check.checked_at < cutoff)
            )
            await db.commit()
            logger.info(f"Retention purge: deleted {result.rowcount} old check records")
        except Exception as e:
            logger.error(f"Retention purge failed: {e}", exc_info=True)
            await db.rollback()