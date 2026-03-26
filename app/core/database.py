from typing import AsyncGenerator, Optional
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.orm import declarative_base
from sqlalchemy.pool import NullPool, AsyncAdaptedQueuePool
from app.core.config import settings
import logging

logger = logging.getLogger(__name__)

# SQL URL to async format
DATABASE_URL = settings.SQLALCHEMY_DATABASE_URI.replace(
    "postgresql://", "postgresql+asyncpg://"
)
# async engine
engine = create_async_engine(
    DATABASE_URL,
    pool_size=settings.DATABASE_POOL_SIZE,
    max_overflow=settings.DATABASE_MAX_OVERFLOW,
    pool_pre_ping=True,
    pool_recycle=3600,  # Recycle connections after 1 hour
    echo=settings.DEBUG,
    poolclass=AsyncAdaptedQueuePool,
    connect_args={
        "command_timeout": 60,
        "timeout": 30,
        "server_settings": {
            "timezone": "UTC",
            "statement_timeout": "30000",  # 30 S
            "lock_timeout": "10000",  # 10 S
        }
    }
)

# Session factory
AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)


Base = declarative_base()

async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """
    Dependency function that yields database sessions."""
    session = AsyncSessionLocal()
    try:
        logger.debug("Database session created")
        yield session
    except Exception as e:
        logger.error(f"Database session error: {e}")
        await session.rollback()
        raise
    finally:
        await session.close()
        logger.debug("Database session closed")
        

async def init_db() -> None:
    """
    Initialize database (create tables if they don't exist)
"""
    async with engine.begin() as conn:
        # Create extensions
        await conn.execute("CREATE EXTENSION IF NOT EXISTS timescaledb CASCADE;")
        await conn.execute("CREATE EXTENSION IF NOT EXISTS uuid-ossp;")
        
        # Create tables
        await conn.run_sync(Base.metadata.create_all)
    
    logger.info("Database initialized successfully")

async def close_db_connections() -> None:
    """
    Close all database connections """
    await engine.dispose()
    logger.info("Database connections closed")

