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

@router.get("/{event_name}", response_model=ChartDataResponse)
async def get_event_data(
    event_name: str,
    start: datetime = Query(..., description="Start time (ISO format)"),
    end: datetime = Query(..., description="End time (ISO format)"),
    bucket: str = Query("1 hour", regex="^(1 minute|5 minutes|15 minutes|30 minutes|1 hour|6 hours|12 hours|1 day|1 week)$"),
    group_by: Optional[str] = Query(None, description="Field to group by (e.g., 'country', 'browser')"),
    filters: Optional[str] = Query(None, description="JSON string of filters"),
    aggregation: str = Query("count", regex="^(count|sum|avg|min|max)$"),
    timezone: str = Query("UTC", description="Timezone for bucket alignment"),
    db: AsyncSession = Depends(get_db),
    redis: RedisClient = Depends(get_redis),
    current_user: User = Depends(get_current_user)
):

  
