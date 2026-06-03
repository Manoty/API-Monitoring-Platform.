from uuid import UUID
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.schemas.endpoint import EndpointCreate, EndpointUpdate, EndpointResponse, EndpointListResponse
from app.services.endpoint_service import (
    create_endpoint, get_endpoint, list_endpoints, update_endpoint, delete_endpoint
)

router = APIRouter(prefix="/endpoints", tags=["Endpoints"])


@router.post("/", response_model=EndpointResponse, status_code=201)
async def register_endpoint(data: EndpointCreate, db: AsyncSession = Depends(get_db)):
    """Register a new API endpoint for monitoring."""
    return await create_endpoint(db, data)


@router.get("/", response_model=EndpointListResponse)
async def list_all_endpoints(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
):
    """List all monitored endpoints with pagination."""
    total, items = await list_endpoints(db, skip=skip, limit=limit)
    return EndpointListResponse(total=total, items=items)


@router.get("/{endpoint_id}", response_model=EndpointResponse)
async def get_endpoint_detail(endpoint_id: UUID, db: AsyncSession = Depends(get_db)):
    """Get a single endpoint by ID."""
    return await get_endpoint(db, endpoint_id)


@router.patch("/{endpoint_id}", response_model=EndpointResponse)
async def update_endpoint_detail(
    endpoint_id: UUID, data: EndpointUpdate, db: AsyncSession = Depends(get_db)
):
    """Update endpoint config or pause/resume monitoring."""
    return await update_endpoint(db, endpoint_id, data)


@router.delete("/{endpoint_id}", status_code=204)
async def remove_endpoint(endpoint_id: UUID, db: AsyncSession = Depends(get_db)):
    """Remove endpoint and all its checks/alerts (cascade)."""
    await delete_endpoint(db, endpoint_id)