import uuid
from datetime import datetime
from sqlalchemy import String, Integer, Float, Boolean, JSON, DateTime, Enum as SAEnum
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.dialects.postgresql import UUID
import enum

from app.core.database import Base


class HttpMethod(str, enum.Enum):
    GET = "GET"
    POST = "POST"
    PUT = "PUT"
    PATCH = "PATCH"
    DELETE = "DELETE"
    HEAD = "HEAD"


class EndpointStatus(str, enum.Enum):
    ACTIVE = "active"       # being monitored
    PAUSED = "paused"       # user paused it
    FAILING = "failing"     # currently down


class Endpoint(Base):
    __tablename__ = "endpoints"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    url: Mapped[str] = mapped_column(String(2048), nullable=False)
    method: Mapped[HttpMethod] = mapped_column(
        SAEnum(HttpMethod), nullable=False, default=HttpMethod.GET
    )

    # what we send
    headers: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    body: Mapped[dict | None] = mapped_column(JSON, nullable=True)

    # what we expect back
    expected_status_code: Mapped[int] = mapped_column(Integer, default=200)

    # scheduling
    interval_seconds: Mapped[int] = mapped_column(Integer, default=60)
    timeout_seconds: Mapped[int] = mapped_column(Integer, default=10)

    # alert thresholds
    latency_threshold_ms: Mapped[float] = mapped_column(Float, default=2000.0)
    max_consecutive_failures: Mapped[int] = mapped_column(Integer, default=3)

    # state
    status: Mapped[EndpointStatus] = mapped_column(
        SAEnum(EndpointStatus), default=EndpointStatus.ACTIVE
    )
    consecutive_failures: Mapped[int] = mapped_column(Integer, default=0)
    last_checked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_success_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow
    )