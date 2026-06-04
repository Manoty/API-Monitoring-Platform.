import pytest
from datetime import datetime, timedelta
from uuid import uuid4

from app.models.check import Check, FailureReason
from app.services.metrics_service import get_metrics_summary, get_uptime_stats

pytestmark = pytest.mark.asyncio


async def seed_checks(db, endpoint_id, results: list[bool]):
    """
    Helper — insert a list of check results into the DB.
    results is a list of booleans: True = success, False = failure.
    """
    base_time = datetime.utcnow() - timedelta(hours=len(results))
    for i, success in enumerate(results):
        check = Check(
            id=uuid4(),
            endpoint_id=endpoint_id,
            success=success,
            status_code=200 if success else 500,
            latency_ms=100.0 + i * 10 if success else None,
            failure_reason=FailureReason.NONE if success else FailureReason.WRONG_STATUS,
            checked_at=base_time + timedelta(hours=i),
        )
        db.add(check)
    await db.commit()


async def test_metrics_summary_success_rate(db, client):
    endpoint_id = uuid4()
    # 7 success, 3 failure = 70% success rate
    await seed_checks(db, endpoint_id, [True] * 7 + [False] * 3)

    summary = await get_metrics_summary(db, endpoint_id)

    assert summary.total_checks == 10
    assert summary.successful_checks == 7
    assert summary.failed_checks == 3
    assert summary.success_rate_percent == 70.0


async def test_metrics_summary_latency(db, client):
    endpoint_id = uuid4()
    await seed_checks(db, endpoint_id, [True, True, True, True])

    summary = await get_metrics_summary(db, endpoint_id)

    assert summary.avg_latency_ms is not None
    assert summary.min_latency_ms is not None
    assert summary.max_latency_ms is not None
    assert summary.p95_latency_ms is not None
    assert summary.min_latency_ms <= summary.avg_latency_ms <= summary.max_latency_ms


async def test_metrics_summary_no_checks(db, client):
    endpoint_id = uuid4()
    summary = await get_metrics_summary(db, endpoint_id)

    assert summary.total_checks == 0
    assert summary.success_rate_percent == 0.0
    assert summary.avg_latency_ms is None


async def test_uptime_100_percent(db, client):
    endpoint_id = uuid4()
    await seed_checks(db, endpoint_id, [True] * 10)

    stats = await get_uptime_stats(db, endpoint_id)

    assert stats.uptime_percent == 100.0
    assert stats.downtime_percent == 0.0
    assert len(stats.downtime_periods) == 0


async def test_uptime_with_downtime_window(db, client):
    endpoint_id = uuid4()
    # success, then 3 failures, then success again = one downtime window
    await seed_checks(db, endpoint_id, [True, False, False, False, True])

    stats = await get_uptime_stats(db, endpoint_id)

    assert stats.uptime_percent == 40.0
    assert len(stats.downtime_periods) == 1
    assert stats.downtime_periods[0].recovered_at is not None


async def test_uptime_still_down(db, client):
    endpoint_id = uuid4()
    # ends on failures — still down
    await seed_checks(db, endpoint_id, [True, True, False, False, False])

    stats = await get_uptime_stats(db, endpoint_id)

    assert len(stats.downtime_periods) == 1
    assert stats.downtime_periods[0].recovered_at is None  # still down