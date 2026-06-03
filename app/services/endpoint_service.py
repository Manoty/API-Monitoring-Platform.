from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from fastapi import HTTPException, status

from app.models.endpoint import Endpoint
from app.schemas.endpoint import EndpointCreate, EndpointUpdate


async def create_endpoint(db: AsyncSession, data: EndpointCreate) -> Endpoint:
    endpoint = Endpoint(
        name=data.name,
        url=str(data.url),
        method=data.method,
        headers=data.headers,
        body=data.body,
        expected_status_code=data.expected_status_code,
        interval_seconds=data.interval_seconds,
        timeout_seconds=data.timeout_seconds,
        latency_threshold_ms=data.latency_threshold_ms,
        max_consecutive_failures=data.max_consecutive_failures,
    )
    db.add(endpoint)
    await db.flush()       # get the ID without full commit
    await db.refresh(endpoint)
    return endpoint


async def get_endpoint(db: AsyncSession, endpoint_id: UUID) -> Endpoint:
    result = await db.execute(select(Endpoint).where(Endpoint.id == endpoint_id))
    endpoint = result.scalar_one_or_none()
    if not endpoint:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Endpoint not found")
    return endpoint


async def list_endpoints(db: AsyncSession, skip: int = 0, limit: int = 50) -> tuple[int, list[Endpoint]]:
    count_result = await db.execute(select(func.count()).select_from(Endpoint))
    total = count_result.scalar()

    result = await db.execute(
        select(Endpoint).order_by(Endpoint.created_at.desc()).offset(skip).limit(limit)
    )
    return total, result.scalars().all()


async def update_endpoint(db: AsyncSession, endpoint_id: UUID, data: EndpointUpdate) -> Endpoint:
    endpoint = await get_endpoint(db, endpoint_id)
    update_data = data.model_dump(exclude_unset=True)   # only update provided fields

    for field, value in update_data.items():
        if field == "url" and value is not None:
            value = str(value)
        setattr(endpoint, field, value)

    await db.flush()
    await db.refresh(endpoint)
    return endpoint


async def delete_endpoint(db: AsyncSession, endpoint_id: UUID) -> None:
    endpoint = await get_endpoint(db, endpoint_id)
    await db.delete(endpoint)