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
  

# Create FastAPI app
app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    openapi_url=f"{settings.API_V1_STR}/openapi.json",
    docs_url="/docs" if settings.DEBUG else None,
    redoc_url="/redoc" if settings.DEBUG else None,
    lifespan=lifespan
)

# Set up CORS
if settings.BACKEND_CORS_ORIGINS:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[str(origin) for origin in settings.BACKEND_CORS_ORIGINS],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

# Add security middleware
app.add_middleware(
    TrustedHostMiddleware,
    allowed_hosts=[str(origin) for origin in settings.BACKEND_CORS_ORIGINS] if settings.BACKEND_CORS_ORIGINS else ["*"]
)

# Include API router
app.include_router(api_router, prefix=settings.API_V1_STR)


# Health check endpoint
@app.get("/health")
async def health_check():
    """
    Health check endpoint for monitoring
    """
    # Check Redis
    redis_healthy = False
    try:
        await redis_client.client.ping()
        redis_healthy = True
    except:
        pass
    
    # Check database
    db_healthy = False
    try:
        async with engine.begin() as conn:
            await conn.execute("SELECT 1")
            db_healthy = True
    except:
        pass
    
    status = "healthy" if redis_healthy and db_healthy else "degraded"
    
    return {
        "status": status,
        "version": settings.VERSION,
        "timestamp": datetime.utcnow().isoformat(),
        "components": {
            "redis": "healthy" if redis_healthy else "unhealthy",
            "database": "healthy" if db_healthy else "unhealthy",
            "api": "healthy"
        }
    }

# Metrics endpoint for Prometheus
@app.get("/metrics")
async def metrics():
    """
    Prometheus metrics endpoint
    """
    from prometheus_client import generate_latest, REGISTRY
    return generate_latest(REGISTRY)

# Root endpoint
@app.get("/")
async def root():
    """
    Root endpoint with service information
    """
    return {
        "service": settings.PROJECT_NAME,
        "version": settings.VERSION,
        "environment": "development" if settings.DEBUG else "production",
        "documentation": "/docs" if settings.DEBUG else None,
        "health_check": "/health",
        "timestamp": datetime.utcnow().isoformat()
    }

if __name__ == "__main__":
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.DEBUG,
        log_level="info",
        workers=1
    )
