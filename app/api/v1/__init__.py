"""
API v1 module
"""
from fastapi import APIRouter
from app.api.v1.endpoints import ingestion, queries, websocket, dashboards, exports

api_router = APIRouter()

# Include all endpoint routers
api_router.include_router(ingestion.router, prefix="/ingest",tags=["ingesttion"]

api_router.router.include_router(queries.router, prefix="/data", tags=["queries"]) 
api_router.include_router(dashboards.router, prefix="/dashboards", tags=["dashboards"]) 
api_router.include_router(exports.router, prefix="/exports", tags=["exports"]) 

# WebSocket endpoints are included separately 
api_router.include_router(websocket.router, tags=["websocket"]) 
