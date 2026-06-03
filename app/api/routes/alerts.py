from uuid import UUID
from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.schemas.alert import AlertListResponse, AlertResponse
from app.services.alert_service import list_alerts, acknowledge_alert

router = APIRouter(prefix="/alerts", tags=["Alerts"])


@router.get("/", response_model=AlertListResponse)
async def fetch_alerts(
    endpoint_id: Optional[UUID] = Query(None),
    unacknowledged_only: bool = Query(False),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
):
    """List all alerts. Filter by endpoint or unacknowledged status."""
    return await list_alerts(db, endpoint_id, unacknowledged_only, skip, limit)


@router.patch("/{alert_id}/acknowledge", response_model=AlertResponse)
async def ack_alert(alert_id: UUID, db: AsyncSession = Depends(get_db)):
    """Mark an alert as acknowledged."""
    return await acknowledge_alert(db, alert_id)