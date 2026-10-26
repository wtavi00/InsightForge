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

    logger.info(f"WebSocket connection attempt - client_id: {client_id}, dashboard: {dashboard_id}, user: {user.get('sub')}")
    await ws_manager.connect(websocket, client_id, dashboard_id, user)      # Accept connection
    pubsub = None      # Subscribe to Redis channel for real-time updates
    try:
        pubsub = await redis.subscribe("event_updates")   # Create Redis pubsub connection
        
        # Send initial connection confirmation
        await websocket.send_json({
            "type": "connection_established",
            "client_id": client_id,
            "dashboard_id": dashboard_id,
            "user_id": user.get("sub"),
            "timestamp": datetime.utcnow().isoformat(),
            "server_time": datetime.utcnow().timestamp()
        })

        # Task for handling incoming messages from client
        async def receive_messages():
            try:
                while True:
                    message = await websocket.receive_text()
                    data = json.loads(message)
                    
                    msg_type = data.get("type")             # Handle different message types
                    if msg_type == "subscribe":
                        new_dashboard = data.get("dashboard_id")
                        if new_dashboard and new_dashboard != dashboard_id:
                            # Move connection-new dashboard
                            await ws_manager.move_connection(
                                websocket, 
                                client_id, 
                                dashboard_id, 
                                new_dashboard,
                                user
                            )
                            dashboard_id = new_dashboard
                            await websocket.send_json({
                                "type": "subscribed",
                                "dashboard_id": dashboard_id,
                                "timestamp": datetime.utcnow().isoformat()
                            })
                            
                            await send_initial_dashboard_data(websocket, dashboard_id, redis)       # Send init data for dashboard
                    
                    elif msg_type == "ping":
                        await websocket.send_json({
                            "type": "pong",
                            "timestamp": datetime.utcnow().timestamp()
                        })
                    
                    elif msg_type == "filter":
                        # Update filters for this connection
                        filters = data.get("filters", {})
                        await ws_manager.update_filters(client_id, filters)
                        
                        await websocket.send_json({
                            "type": "filters_updated",
                            "filters": filters,
                            "timestamp": datetime.utcnow().isoformat()
                        })
                    
                    elif msg_type == "unsubscribe":
                        await ws_manager.disconnect(websocket, client_id, dashboard_id)
                        await websocket.close()
                        break
