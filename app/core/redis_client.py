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

    async def delete(self, *keys: str) -> int:
        """
        Delete keys from cache
        """
        try:
            return await self.client.delete(*keys)
        except Exception as e:
            logger.error(f"Redis delete error for keys {keys}: {e}")
            return 0

    async def exists(self, key: str) -> bool:
        """
        Check if key exists
        """
        try:
            return await self.client.exists(key) > 0
        except Exception as e:
            logger.error(f"Redis exists error for key {key}: {e}")
            return False
            
    async def expire(self, key: str, ttl: int) -> bool:
        """
        Set expiration on key
        """
        try:
            return await self.client.expire(key, ttl)
        except Exception as e:
            logger.error(f"Redis expire error for key {key}: {e}")
            return False

    async def ttl(self, key: str) -> int:
        """
        Get TTL of key
        """
        try:
            return await self.client.ttl(key)
        except Exception as e:
            logger.error(f"Redis ttl error for key {key}: {e}")
            return -2

    async def incr(self, key: str, amount: int = 1) -> Optional[int]:
        """
        Increment counter
        """
        try:
            return await self.client.incr(key, amount)
        except Exception as e:
            logger.error(f"Redis incr error for key {key}: {e}")
            return None
            
    async def decr(self, key: str, amount: int = 1) -> Optional[int]:
        """
        Decrement counter
        """
        try:
            return await self.client.decr(key, amount)
        except Exception as e:
            logger.error(f"Redis decr error for key {key}: {e}")
            return None
            
    async def hset(self, key: str, field: str, value: Any) -> bool:
        """
        Set hash field
        """
        try:
            if isinstance(value, (dict, list)):
                value = json.dumps(value)
            await self.client.hset(key, field, value)
            return True
        except Exception as e:
            logger.error(f"Redis hset error for key {key}: {e}")
            return False

    async def hget(self, key: str, field: str, default: Any = None) -> Any:
        """
        Get hash field
        """
        try:
            value = await self.client.hget(key, field)
            if value:
                try:
                    return json.loads(value)
                except:
                    return value.decode('utf-8') if isinstance(value, bytes) else value
            return default
        except Exception as e:
            logger.error(f"Redis hget error for key {key}: {e}")
            return default

    async def hgetall(self, key: str) -> dict:
        """
        Get all hash fields
        """
        try:
            result = {}
            data = await self.client.hgetall(key)
            for k, v in data.items():
                try:
                    result[k.decode('utf-8')] = json.loads(v)
                except:
                    result[k.decode('utf-8')] = v.decode('utf-8') if isinstance(v, bytes) else v
            return result
        except Exception as e:
            logger.error(f"Redis hgetall error for key {key}: {e}")
            return {}
            
    async def publish(self, channel: str, message: Any):
        """
        Publish message to channel
        """
        try:
            if isinstance(message, (dict, list)):
                message = json.dumps(message)
            await self.client.publish(channel, message)
        except Exception as e:
            logger.error(f"Redis publish error to channel {channel}: {e}")
            
    async def subscribe(self, channel: str) -> redis.client.PubSub:
        """
        Subscribe to channel
        """
        try:
            pubsub = self.client.pubsub()
            await pubsub.subscribe(channel)
            self._pubsub_connections.append(pubsub)
            return pubsub
        except Exception as e:
            logger.error(f"Redis subscribe error to channel {channel}: {e}")
            raise

    async def keys(self, pattern: str = "*") -> List[str]:
        """
        Get keys matching pattern
        """
        try:
            keys = await self.client.keys(pattern)
            return [k.decode('utf-8') if isinstance(k, bytes) else k for k in keys]
        except Exception as e:
            logger.error(f"Redis keys error for pattern {pattern}: {e}")
            return []
