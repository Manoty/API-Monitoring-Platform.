from pydantic import BaseModel
from typing import Optional
from datetime import datetime
from uuid import UUID


class DowntimePeriod(BaseModel):
    started_at: datetime
    recovered_at: Optional[datetime]       # None means still down
    duration_seconds: Optional[float]


class UptimeStats(BaseModel):
    endpoint_id: UUID
    uptime_percent: float
    downtime_percent: float
    total_checks: int
    successful_checks: int
    failed_checks: int
    downtime_periods: list[DowntimePeriod]
    from_time: datetime
    to_time: datetime