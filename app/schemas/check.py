from pydantic import BaseModel
from typing import Optional
from datetime import datetime
from uuid import UUID

from app.models.check import FailureReason


class CheckResponse(BaseModel):
    id: UUID
    endpoint_id: UUID
    success: bool
    status_code: Optional[int]
    latency_ms: Optional[float]
    failure_reason: FailureReason
    error_message: Optional[str]
    checked_at: datetime

    model_config = {"from_attributes": True}


class MetricsSummary(BaseModel):
    endpoint_id: UUID
    total_checks: int
    successful_checks: int
    failed_checks: int
    success_rate_percent: float
    avg_latency_ms: Optional[float]
    min_latency_ms: Optional[float]
    max_latency_ms: Optional[float]
    p95_latency_ms: Optional[float]        # 95th percentile — more useful than avg
    from_time: datetime
    to_time: datetime


class CheckListResponse(BaseModel):
    total: int
    items: list[CheckResponse]