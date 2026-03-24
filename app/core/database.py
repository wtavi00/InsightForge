from typing import AsyncGenerator, Optional
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.orm import declarative_base
from sqlalchemy.pool import NullPool, AsyncAdaptedQueuePool
from app.core.config import settings
import logging

logger = logging.getLogger(__name__)

# Convert PostgreSQL URL to async format
DATABASE_URL = settings.SQLALCHEMY_DATABASE_URI.replace(
    "postgresql://", "postgresql+asyncpg://"
)
