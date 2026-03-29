import json
import pickle
from typing import Optional, Any, Union, List
import redis.asyncio as redis
from redis.asyncio.connection import ConnectionPool
from app.core.config import settings
import logging
from datetime import timedelta
import asyncio

logger = logging.getLogger(__name__)

class RedisClient:
    def __init__(self):
        self.client: Optional[redis.Redis] = None
        self.pool: Optional[ConnectionPool] = None
        self._pubsub_connections = []

    async def initialize(self):
        """
        Initialize Redis connection pool
        """
        try:
            self.pool = ConnectionPool.from_url(
                settings.REDIS_URI,
                max_connections=settings.REDIS_MAX_CONNECTIONS,
                socket_timeout=settings.REDIS_SOCKET_TIMEOUT,
                socket_connect_timeout=settings.REDIS_SOCKET_CONNECT_TIMEOUT,
                retry_on_timeout=settings.REDIS_RETRY_ON_TIMEOUT,
                health_check_interval=30,
            )
            
            self.client = redis.Redis(
                connection_pool=self.pool,
                decode_responses=False  # Keeping as bytes (binary data)
            )
          
