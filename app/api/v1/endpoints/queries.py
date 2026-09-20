from fastapi import APIRouter, Depends, HTTPException, Query 
from typing import Optional, List, Dict, Any 
from datetime import datetime, timedelta 
from sqlalchemy.ext.asyncio import AsyncSession 
import json 
import logging

from app.api.v1.models.responses import chartDataResponse, TimeSeriesPoint, metrcsSummary
from app.services.query_service import QueryService
from app.services.cache_service import CacheService
from app.core.database import get_db
from app.core.redis_clint import get_redis, redisClint
from app.core.auth import get_current_user
from app.api.v1.models.dashboard import User

router = APIRouter()
logger = logging.getLogger(__name__)

