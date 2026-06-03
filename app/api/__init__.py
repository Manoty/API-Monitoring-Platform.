from fastapi import APIRouter
from app.api.routes import endpoints, metrics, alerts

api_router = APIRouter()
api_router.include_router(endpoints.router)
api_router.include_router(metrics.router)
api_router.include_router(alerts.router)