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

    """
    Get aggregated event data for charts
    
    - **event_name**: Name of the event to query
    - **start**: Start time in ISO format
    - **end**: End time in ISO format
    - **bucket**: Time bucket for aggregation
    - **group_by**: Field to group results by
    - **filters**: JSON string of filters (e.g., {"country": "US", "browser": "Chrome"})
    - **aggregation**: Aggregation function to apply
    - **timezone**: Timezone for bucket alignment
    """
    try:
        # Validate date range
        if end <= start:
            raise HTTPException(status_code=400, detail="End time must be after start time")
        
        max_range = timedelta(days=90)
        if (end - start) > max_range:
            raise HTTPException(
                status_code=400, 
                detail=f"Date range cannot exceed 90 days. Requested: {(end - start).days} days"
            )
        # Initialize services
        query_service = QueryService(db)
        cache_service = CacheService(redis)
        
        # Parse filters if provided
        filter_dict = {}
        if filters:
            try:
                filter_dict = json.loads(filters)
                if not isinstance(filter_dict, dict):
                    raise ValueError("Filters must be a JSON object")
            except json.JSONDecodeError:
                raise HTTPException(status_code=400, detail="Invalid filters JSON")
        
        # Generate cache key
        cache_key = cache_service.generate_key(
            "data",
            event_name=event_name,
            start=start.isoformat(),
            end=end.isoformat(),
            bucket=bucket,
            group_by=group_by,
            filters=filter_dict,
            aggregation=aggregation,
            user_id=str(current_user.id)
        )

"""
provided pattern is not valid till you put the adject 
querry in the logind to the patr you want to get the enter value of 
mathametical solutions for the edject return value for liner or constant structure
"""
