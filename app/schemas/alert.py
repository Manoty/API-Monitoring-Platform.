from pydantic import BaseModel
from typing import Optional
from datetime import datetime
from uuid import UUID

from app.models.alert import AlertType, AlertSeverity


class AlertResponse(BaseModel):
    id: UUID
    endpoint_id: UUID
    alert_type: AlertType
    severity: AlertSeverity
    message: str
    acknowledged: bool
    acknowledged_at: Optional[datetime]
    triggered_at: datetime

    model_config = {"from_attributes": True}


class AlertAcknowledge(BaseModel):
    acknowledged: bool = True


class AlertListResponse(BaseModel):
    total: int
    items: list[AlertResponse]