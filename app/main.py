from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from contextlib import asynccontextmanager
import logging
import uvicorn
from datetime import datetime

from app.core.config import settings
from app.core.redis_client import redis_client
from app.api.v1.api import api_router
from app.core.logging import setup_logging
from app.core.database import engine
from app.websocket.manager import ws_manager


# Setup logging
setup_logging()
logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Lifespan context manager for startup and shutdown events 
    """
    # Startup
    logger.info("Starting up Analytics Dashboard Service...")
    logger.info(f"Environment: {'development' if settings.DEBUG else 'production'}")
    logger.info(f"Version: {settings.VERSION}")
    
    # Redis Initialization
    try:
        await redis_client.initialize()
        logger.info("Redis client initialized successfully")
    except Exception as e:
        logger.error(f"Failed to initialize Redis: {e}")
        raise
    
    # Initialize database connection pool
    try:
        async with engine.begin() as conn:
            await conn.execute("SELECT 1")
        logger.info("Database connection pool initialized")
    except Exception as e:
        logger.error(f"Failed to initialize database: {e}")
        raise
    
    yield
    
    # Shutdown
    logger.info("Shutting down Analytics Dashboard Service...")
    
    # Close Redis connection
    await redis_client.close()
    
    # Close database connections
    await engine.dispose()
    
    # Clear websocket connections
    ws_manager.active_connections.clear()
    ws_manager.user_connections.clear()
    
    logger.info("Shutdown complete")
  
