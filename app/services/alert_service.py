from uuid import UUID
from typing import Optional
from datetime import datetime

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from fastapi import HTTPException, status

from app.models.alert import Alert, AlertType, AlertSeverity
from app.models.endpoint import Endpoint
from app.schemas.alert import AlertListResponse, AlertResponse
from app.core.logging import get_logger

logger = get_logger(__name__)


async def create_alert(
    db: AsyncSession,
    endpoint: Endpoint,
    alert_type: AlertType,
    severity: AlertSeverity,
    message: str,
) -> Alert:
    alert = Alert(
        endpoint_id=endpoint.id,
        alert_type=alert_type,
        severity=severity,
        message=message,
    )
    db.add(alert)
    await db.flush()

    # log it regardless of email config
    logger.warning(
        f"ALERT [{severity.upper()}] | {alert_type} | endpoint={endpoint.name} | {message}"
    )
    return alert


async def list_alerts(
    db: AsyncSession,
    endpoint_id: Optional[UUID] = None,
    unacknowledged_only: bool = False,
    skip: int = 0,
    limit: int = 50,
) -> AlertListResponse:
    query = select(Alert)

    if endpoint_id:
        query = query.where(Alert.endpoint_id == endpoint_id)
    if unacknowledged_only:
        query = query.where(Alert.acknowledged == False)

    count_result = await db.execute(
        select(func.count()).select_from(query.subquery())
    )
    total = count_result.scalar()

    result = await db.execute(
        query.order_by(Alert.triggered_at.desc()).offset(skip).limit(limit)
    )
    alerts = result.scalars().all()

    return AlertListResponse(
        total=total,
        items=[AlertResponse.model_validate(a) for a in alerts],
    )


async def acknowledge_alert(db: AsyncSession, alert_id: UUID) -> Alert:
    result = await db.execute(select(Alert).where(Alert.id == alert_id))
    alert = result.scalar_one_or_none()
    if not alert:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Alert not found")

    alert.acknowledged = True
    alert.acknowledged_at = datetime.utcnow()
    await db.flush()
    await db.refresh(alert)
    return alert