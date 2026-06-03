from uuid import UUID
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.schemas.check import MetricsSummary, CheckListResponse
from app.schemas.uptime import UptimeStats
from app.services.metrics_service import get_checks, get_metrics_summary, get_uptime_stats

router = APIRouter(tags=["Metrics"])


@router.get("/metrics/{endpoint_id}", response_model=CheckListResponse)
async def fetch_check_history(
    endpoint_id: UUID,
    from_time: Optional[datetime] = Query(None),
    to_time: Optional[datetime] = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    db: AsyncSession = Depends(get_db),
):
    """Paginated raw check history for an endpoint."""
    return await get_checks(db, endpoint_id, from_time, to_time, skip, limit)


@router.get("/metrics/{endpoint_id}/summary", response_model=MetricsSummary)
async def fetch_metrics_summary(
    endpoint_id: UUID,
    from_time: Optional[datetime] = Query(None),
    to_time: Optional[datetime] = Query(None),
    db: AsyncSession = Depends(get_db),
):
    """Aggregated stats: success rate, avg/min/max/p95 latency."""
    return await get_metrics_summary(db, endpoint_id, from_time, to_time)


@router.get("/uptime/{endpoint_id}", response_model=UptimeStats)
async def fetch_uptime(
    endpoint_id: UUID,
    from_time: Optional[datetime] = Query(None),
    to_time: Optional[datetime] = Query(None),
    db: AsyncSession = Depends(get_db),
):
    """Uptime percentage + downtime windows for an endpoint."""
    return await get_uptime_stats(db, endpoint_id, from_time, to_time)