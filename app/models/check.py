import uuid
from datetime import datetime
from sqlalchemy import String, Integer, Float, Boolean, DateTime, ForeignKey, Text, Enum as SAEnum, Index
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.dialects.postgresql import UUID
import enum

from app.core.database import Base


class FailureReason(str, enum.Enum):
    NONE = "none"
    TIMEOUT = "timeout"
    CONNECTION_ERROR = "connection_error"
    WRONG_STATUS = "wrong_status"
    NETWORK_ERROR = "network_error"
    SSL_ERROR = "ssl_error"


class Check(Base):
    __tablename__ = "checks"

    # composite index on (endpoint_id, checked_at DESC) — all time-range queries use this
    __table_args__ = (
        Index("ix_checks_endpoint_time", "endpoint_id", "checked_at"),
        Index("ix_checks_checked_at", "checked_at"),  # for retention cleanup queries
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    endpoint_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("endpoints.id", ondelete="CASCADE"), nullable=False
    )

    # result
    success: Mapped[bool] = mapped_column(Boolean, nullable=False)
    status_code: Mapped[int | None] = mapped_column(Integer, nullable=True)      # None on network error
    latency_ms: Mapped[float | None] = mapped_column(Float, nullable=True)       # None on timeout

    failure_reason: Mapped[FailureReason] = mapped_column(
        SAEnum(FailureReason), default=FailureReason.NONE
    )
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)

    checked_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow, nullable=False
    )