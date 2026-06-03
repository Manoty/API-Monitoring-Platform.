from pydantic import BaseModel, HttpUrl, Field
from typing import Optional
from datetime import datetime
from uuid import UUID

from app.models.endpoint import HttpMethod, EndpointStatus


class EndpointCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    url: HttpUrl
    method: HttpMethod = HttpMethod.GET
    headers: dict = Field(default_factory=dict)
    body: Optional[dict] = None
    expected_status_code: int = Field(default=200, ge=100, le=599)
    interval_seconds: int = Field(default=60, ge=10, le=86400)   # min 10s, max 1 day
    timeout_seconds: int = Field(default=10, ge=1, le=60)
    latency_threshold_ms: float = Field(default=2000.0, gt=0)
    max_consecutive_failures: int = Field(default=3, ge=1, le=100)


class EndpointUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    url: Optional[HttpUrl] = None
    method: Optional[HttpMethod] = None
    headers: Optional[dict] = None
    body: Optional[dict] = None
    expected_status_code: Optional[int] = Field(None, ge=100, le=599)
    interval_seconds: Optional[int] = Field(None, ge=10, le=86400)
    timeout_seconds: Optional[int] = Field(None, ge=1, le=60)
    latency_threshold_ms: Optional[float] = Field(None, gt=0)
    max_consecutive_failures: Optional[int] = Field(None, ge=1, le=100)
    status: Optional[EndpointStatus] = None


class EndpointResponse(BaseModel):
    id: UUID
    name: str
    url: str
    method: HttpMethod
    headers: dict
    body: Optional[dict]
    expected_status_code: int
    interval_seconds: int
    timeout_seconds: int
    latency_threshold_ms: float
    max_consecutive_failures: int
    status: EndpointStatus
    consecutive_failures: int
    last_checked_at: Optional[datetime]
    last_success_at: Optional[datetime]
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class EndpointListResponse(BaseModel):
    total: int
    items: list[EndpointResponse]