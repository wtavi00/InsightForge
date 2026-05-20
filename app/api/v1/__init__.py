"""
API v1 module
"""
from fastapi import APIRouter
from app.api.v1.endpoints import ingestion, queries, websocket, dashboards, exports

api_router = APIRouter()

# Include all endpoint routers
api_router.include_router(ingestion.router, prefix="/ingest",tags=["ingesttion"]
