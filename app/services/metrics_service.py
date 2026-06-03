from uuid import UUID
from datetime import datetime, timedelta
from typing import Optional
import statistics

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from app.models.check import Check, FailureReason
from app.schemas.check import MetricsSummary, CheckListResponse, CheckResponse
from app.schemas.uptime import UptimeStats, DowntimePeriod


async def get_checks(
    db: AsyncSession,
    endpoint_id: UUID,
    from_time: Optional[datetime] = None,
    to_time: Optional[datetime] = None,
    skip: int = 0,
    limit: int = 100,
) -> CheckListResponse:
    if not from_time:
        from_time = datetime.utcnow() - timedelta(hours=24)
    if not to_time:
        to_time = datetime.utcnow()

    base_query = (
        select(Check)
        .where(Check.endpoint_id == endpoint_id)
        .where(Check.checked_at >= from_time)
        .where(Check.checked_at <= to_time)
    )

    count_result = await db.execute(
        select(func.count()).select_from(base_query.subquery())
    )
    total = count_result.scalar()

    result = await db.execute(
        base_query.order_by(Check.checked_at.desc()).offset(skip).limit(limit)
    )
    checks = result.scalars().all()

    return CheckListResponse(
        total=total,
        items=[CheckResponse.model_validate(c) for c in checks],
    )


async def get_metrics_summary(
    db: AsyncSession,
    endpoint_id: UUID,
    from_time: Optional[datetime] = None,
    to_time: Optional[datetime] = None,
) -> MetricsSummary:
    if not from_time:
        from_time = datetime.utcnow() - timedelta(hours=24)
    if not to_time:
        to_time = datetime.utcnow()

    result = await db.execute(
        select(Check)
        .where(Check.endpoint_id == endpoint_id)
        .where(Check.checked_at >= from_time)
        .where(Check.checked_at <= to_time)
        .order_by(Check.checked_at)
    )
    checks = result.scalars().all()

    total = len(checks)
    successful = sum(1 for c in checks if c.success)
    latencies = [c.latency_ms for c in checks if c.latency_ms is not None]

    # p95 — sort latencies, take value at 95th percentile index
    p95 = None
    if latencies:
        sorted_lat = sorted(latencies)
        p95_index = int(len(sorted_lat) * 0.95)
        p95 = sorted_lat[min(p95_index, len(sorted_lat) - 1)]

    return MetricsSummary(
        endpoint_id=endpoint_id,
        total_checks=total,
        successful_checks=successful,
        failed_checks=total - successful,
        success_rate_percent=round((successful / total * 100), 2) if total > 0 else 0.0,
        avg_latency_ms=round(statistics.mean(latencies), 2) if latencies else None,
        min_latency_ms=min(latencies) if latencies else None,
        max_latency_ms=max(latencies) if latencies else None,
        p95_latency_ms=round(p95, 2) if p95 else None,
        from_time=from_time,
        to_time=to_time,
    )


async def get_uptime_stats(
    db: AsyncSession,
    endpoint_id: UUID,
    from_time: Optional[datetime] = None,
    to_time: Optional[datetime] = None,
) -> UptimeStats:
    if not from_time:
        from_time = datetime.utcnow() - timedelta(days=7)
    if not to_time:
        to_time = datetime.utcnow()

    result = await db.execute(
        select(Check)
        .where(Check.endpoint_id == endpoint_id)
        .where(Check.checked_at >= from_time)
        .where(Check.checked_at <= to_time)
        .order_by(Check.checked_at.asc())   # oldest first to walk the timeline
    )
    checks = result.scalars().all()

    total = len(checks)
    successful = sum(1 for c in checks if c.success)

    # walk checks in order, detect downtime windows
    downtime_periods: list[DowntimePeriod] = []
    downtime_start: Optional[datetime] = None

    for check in checks:
        if not check.success and downtime_start is None:
            downtime_start = check.checked_at   # failure streak starts
        elif check.success and downtime_start is not None:
            duration = (check.checked_at - downtime_start).total_seconds()
            downtime_periods.append(DowntimePeriod(
                started_at=downtime_start,
                recovered_at=check.checked_at,
                duration_seconds=duration,
            ))
            downtime_start = None

    # still down at end of window
    if downtime_start is not None:
        downtime_periods.append(DowntimePeriod(
            started_at=downtime_start,
            recovered_at=None,
            duration_seconds=None,
        ))

    uptime_pct = round((successful / total * 100), 3) if total > 0 else 100.0

    return UptimeStats(
        endpoint_id=endpoint_id,
        uptime_percent=uptime_pct,
        downtime_percent=round(100.0 - uptime_pct, 3),
        total_checks=total,
        successful_checks=successful,
        failed_checks=total - successful,
        downtime_periods=downtime_periods,
        from_time=from_time,
        to_time=to_time,
    )