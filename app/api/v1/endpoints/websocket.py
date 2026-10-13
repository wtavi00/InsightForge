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
