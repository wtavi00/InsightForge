"""
API v1 module
"""
from fastapi import APIRouter
from app.api.v1.endpoints import ingestion, queries, websocket, dashboards, exports

api_router = APIRouter()

api_router.include_router(ingestion.router, prefix="/ingest",tags=["ingesttion"]  # include all endpoints

api_router.router.include_router(queries.router, prefix="/data", tags=["queries"]) 
api_router.include_router(dashboards.router, prefix="/dashboards", tags=["dashboards"]) 
api_router.include_router(exports.router, prefix="/exports", tags=["exports"]) 

api_router.include_router(websocket.router, tags=["websocket"])   # websocket endpoint will be added seperately
