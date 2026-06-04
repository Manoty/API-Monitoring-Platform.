from uuid import UUID
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.schemas.endpoint import EndpointCreate, EndpointUpdate, EndpointResponse, EndpointListResponse
from app.services.endpoint_service import (
    create_endpoint, get_endpoint, list_endpoints, update_endpoint, delete_endpoint
)
from app.workers.scheduler import schedule_endpoint, unschedule_endpoint
from app.models.endpoint import EndpointStatus

router = APIRouter(prefix="/endpoints", tags=["Endpoints"])


@router.post("/", response_model=EndpointResponse, status_code=201)
async def register_endpoint(data: EndpointCreate, db: AsyncSession = Depends(get_db)):
    """Register a new endpoint and immediately schedule it."""
    endpoint = await create_endpoint(db, data)
    schedule_endpoint(endpoint)          # live — starts monitoring right away
    return endpoint


@router.get("/", response_model=EndpointListResponse)
async def list_all_endpoints(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
):
    total, items = await list_endpoints(db, skip=skip, limit=limit)
    return EndpointListResponse(total=total, items=items)


@router.get("/{endpoint_id}", response_model=EndpointResponse)
async def get_endpoint_detail(endpoint_id: UUID, db: AsyncSession = Depends(get_db)):
    return await get_endpoint(db, endpoint_id)


@router.patch("/{endpoint_id}", response_model=EndpointResponse)
async def update_endpoint_detail(
    endpoint_id: UUID, data: EndpointUpdate, db: AsyncSession = Depends(get_db)
):
    """Update endpoint. If paused — unschedule. If reactivated — reschedule."""
    endpoint = await update_endpoint(db, endpoint_id, data)

    if endpoint.status == EndpointStatus.PAUSED:
        unschedule_endpoint(str(endpoint_id))
    else:
        schedule_endpoint(endpoint)      # reschedule with updated interval if changed

    return endpoint


@router.delete("/{endpoint_id}", status_code=204)
async def remove_endpoint(endpoint_id: UUID, db: AsyncSession = Depends(get_db)):
    """Delete endpoint and stop monitoring it."""
    unschedule_endpoint(str(endpoint_id))
    await delete_endpoint(db, endpoint_id)