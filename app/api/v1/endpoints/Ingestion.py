from fastapi import APIRouter, Depends, HTTPException, Request, BackgroundTasks
from typing import List, Optional
import logging
from datetime import datetime
from uuid import UUID

from app.api.v1.models.event import EventCreate, EventBatch, EventResponse 
from app.workers.tasks.event_tasks import process_event, process_event_batch 
from app.core.security import validate_api_key 
from app.utils.validators import validate_event_data 
from app.utils.enrichers import enrich_event_data 
from app.core.rate_limiter import RateLimiter 
from app.core.redis_client import get_redis, RedisClient 
from app.core.config import settings

router = APIRouter() 
logger = logging.getLogger(__name__)

# Initialize rate limiter 
rate_limiter = RateLimiter( 
    redis_client=None, # Will be set in dependency 
    rate_per_second=settings.RATE_LIMIT_PER_SECOND, 
    rate_per_minute=settings.RATE_LIMIT_PER_MINUTE 
    ) 
