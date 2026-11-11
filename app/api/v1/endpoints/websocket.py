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
                        
            except WebSocketDisconnect:
                raise
            except json.JSONDecodeError:
                logger.warning(f"Invalid JSON received from client {client_id}")
                await websocket.send_json({
                    "type": "error",
                    "message": "Invalid JSON format",
                    "timestamp": datetime.utcnow().isoformat()
                })
            except Exception as e:
                logger.error(f"Error receiving message from {client_id}: {e}")
        
        # Handling Redis messages
        async def handle_redis_messages():
            try:
                async for message in pubsub.listen():
                    if message["type"] == "message":
                        try:
                            data = json.loads(message["data"])
                            
                            # Check if this update is compatable to this client
                            if await ws_manager.should_send_update(client_id, data, dashboard_id):
                                await websocket.send_json({
                                    "type": "live_update",
                                    "data": data,
                                    "timestamp": datetime.utcnow().isoformat()
                                })
                        except json.JSONDecodeError:
                            logger.error(f"Invalid JSON in Redis message: {message['data']}")
                        except Exception as e:
                            logger.error(f"Error processing Redis message: {e}")
            except asyncio.CancelledError:
                pass
            except Exception as e:
                logger.error(f"Error in Redis message handler: {e}")
        
        # Sending heartbeat
        async def send_heartbeat():
            try:
                while True:
                    await asyncio.sleep(30)  # Send heartbeat every 30 seconds
                    await websocket.send_json({
                        "type": "heartbeat",
                        "timestamp": datetime.utcnow().timestamp()
                    })
            except asyncio.CancelledError:
                pass
            except Exception as e:
                logger.error(f"Error sending heartbeat: {e}")

        # Run all tasks concurrently
        tasks = [
            asyncio.create_task(receive_messages()),
            asyncio.create_task(handle_redis_messages()),
            asyncio.create_task(send_heartbeat())
        ]
        done, pending = await asyncio.wait(tasks, return_when=asyncio.FIRST_COMPLETED)
        
        for task in pending:
            task.cancel()       # Cancel pending tasks after 3 seconds
            try:
                await task
            except asyncio.CancelledError:
                pass
