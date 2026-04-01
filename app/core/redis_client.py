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
          
            await self.client.ping() # Test
            logger.info(f"Redis client initialized successfully (pool size: {settings.REDIS_MAX_CONNECTIONS})")
        except Exception as e:
            logger.error(f"Failed to initialize Redis: {e}")
            raise
            
    async def close(self):
        """
        Close all Redis connections
        """
        if self.pool:
            await self.pool.disconnect()
            logger.info("Redis connection pool closed")
        
        for pubsub in self._pubsub_connections:  # pubsub connection closed
            await pubsub.close()
        self._pubsub_connections.clear()

    async def get(self, key: str, default: Any = None) -> Optional[Any]:
        """
        Get value from cache
        """
        try:
            value = await self.client.get(key)
            if value:
                try:
                    return json.loads(value)
                except:
                    try:
                        return pickle.loads(value)
                    except:
                        return value.decode('utf-8') if isinstance(value, bytes) else value
            return default
        except Exception as e:
            logger.error(f"Redis get error for key {key}: {e}")
            return default
            
    async def set(self, key: str, value: Any, ttl: int = settings.CACHE_TTL) -> bool:
        """
        Set value in cache with TTL
        """
        try:
            if isinstance(value, (dict, list)):
                value = json.dumps(value)
            elif not isinstance(value, (str, bytes)):
                value = pickle.dumps(value)
            await self.client.setex(key, ttl, value)
            return True
        except Exception as e:
            logger.error(f"Redis set error for key {key}: {e}")
            return False

    async def set_nx(self, key: str, value: Any, ttl: int = settings.CACHE_TTL) -> bool:
        """
        Set if not exists
        """
        try:
            if isinstance(value, (dict, list)):
                value = json.dumps(value)
            elif not isinstance(value, (str, bytes)):
                value = pickle.dumps(value)

            result = await self.client.setnx(key, value)
            if result:
                await self.client.expire(key, ttl)
            return bool(result)
        except Exception as e:
            logger.error(f"Redis set_nx error for key {key}: {e}")
            return False

