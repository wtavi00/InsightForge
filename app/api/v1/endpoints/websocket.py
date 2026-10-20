from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends, Query
from typing import Optional, Dict, Any
import json
import logging
from datetime import datetime
import asyncio

from app.websocket.manager import ws_manager
from app.core.security import verify_websocket_token
from app.core.redis_client import get_redis, RedisClient
from app.core.config import settings

router = APIRouter()
logger = logging.getLogger(__name__)

@router.websocket("/ws/live")
async def websocket_live(
    websocket: WebSocket,
    client_id: str = Query(..., description="Client identifier"),
    dashboard_id: Optional[str] = Query(None, description="Dashboard to subscribe to"),
    token: str = Query(..., description="Authentication token"),
    redis: RedisClient = Depends(get_redis)
):
    """
    WebSocket endpoint for real-time updates
    
    - **client_id**: Unique client identifier
    - **dashboard_id**: Optional dashboard ID to subscribe to
    - **token**: JWT authentication token
    """
    # Verify authentication
    user = await verify_websocket_token(token)
    if not user:
        logger.warning(f"WebSocket authentication failed for client {client_id}")
        await websocket.close(code=1008, reason="Invalid authentication")
        return
