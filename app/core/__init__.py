from app.core.config import settings
from app.core.database import get_db
from app.core.redis_client import redis_client, get_redis
"""
Core module containing configuration and shared utilities
"""
__all__ = ["settings", "get_db", "redis_client", "get_redis"]
