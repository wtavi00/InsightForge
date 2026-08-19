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

@router.post("", response_model=EventResponse, status_code=202) 
async def ingest_event( 
    request: Request, 
    event: EventCreate, 
    background_tasks: BackgroundTasks, a
    api_key: str = Depends(validate_api_key), 
    redis: RedisClient = Depends(get_redis) 
):
    """
    Ingest a single analytics event
    - **event_name**: Name of the event (e.g., page_view, purchase) 
    - **user_id**: Optional user identifier 
    - **session_id**: Optional session identifier 
    - **properties**: Additional event properties (JSON object) 
    - **value**: Optional numeric value 
    - **timestamp**: Event timestamp (defaults to current UTC time) 
    """ 
    try: # Update rate limiter with redis client 
        rate_limiter.redis = redis
        await rate_limiter.check_limit(api_key)
        validation_result = validate_event_data(event.dict()) 
            if not validation_result["valid"]: 
                raise HTTPException( 
                    status_code=400, 
                    detail={"message": "Event validation failed", "errors": validation_result["errors"]} 
                )
            
        # Enrich event with additional data 
        enriched_event = await enrich_event_data( 
            event.dict(), 
            client_ip=request.client.host if request.client else None, 
            user_agent=request.headers.get("user-agent"), 
            headers=dict(request.headers) 
        ) 
        #Add to processing queue 
        background_tasks.add_task( 
            process_event.delay, 
            enriched_event
        ) 
        logger.info(f"Event {event.event_id} ingested successfully", extra={ 
            "event_id": str(event.event_id), 
            "event_name": event.event_name, 
            "api_key": api_key[:8] + "..." # Log partial key for security
        }) 
        return EventResponse( 
            event_id=event.event_id, 
            status="accepted", 
            message="Event queued for processing", 
            timestamp=datetime.utcnow() 
        ) 
    except HTTPException: 
        raise 
    except Exception as e: 
        logger.error(f"Error ingesting event: {e}", exc_info=True) 
        raise HTTPException(status_code=500, detail="Internal server error")

@router.post("/batch", response_model=dict, status_code=202) 
async def ingest_event_batch( 
    request: Request, 
    batch: EventBatch, 
    background_tasks: BackgroundTasks, 
    api_key: str = Depends(validate_api_key), 
    redis: RedisClient = Depends(get_redis) 
):
    """ 
    Ingest a batch of analytics events (up to 1000 events per batch) 
    - **events**: List of events to ingest 
    - **api_key**: API key for authentication 
    """ 
    try: 
        # Update rate limiter with redis client 
        rate_limiter.redis = redis # Validate batch size 
        if len(batch.events) > 1000: 
            raise HTTPException( 
                status_code=400, 
                detail="Batch size cannot exceed 1000 events" 
            ) 
        # Check rate limit (count each event in batch) 
        await rate_limiter.check_limit(api_key, count=len(batch.events)) 
        # Validate and enrich each event 
        enriched_events = [] 
        validation_errors = [] 
        for i, event in enumerate(batch.events): 
            # Validate event 
            validation_result = validate_event_data(event.dict()) 
            if not validation_result["valid"]: 
                validation_errors.append({ 
                    "index": i, 
                    "event_id": str(event.event_id), 
                    "errors": validation_result["errors"] 
                }) 
                continue 
                #Enrich event 
                enriched = await enrich_event_data( 
                    event.dict(), 
                    client_ip=request.client.host if request.client else None, 
                    user_agent=request.headers.get("user-agent"), 
                    headers=dict(request.headers) 
                ) 
                enriched_events.append(enriched)

        # If there were validation errors, return partial success 
            if validation_errors: 
                if not enriched_events: 
                    raise HTTPException( 
                        status_code=400, 
                        detail={"message": "All events failed validation", "errors": validation_errors} 
                    )
                    
                #Process valid events 
                background_tasks.add_task( 
                    process_event_batch.delay, 
                    enriched_events 
                ) 
                return { 
                    "status": "partial_success", 
                    "accepted_count": len(enriched_events), 
                    "failed_count": len(validation_errors), 
                    "errors": validation_errors, 
                    "timestamp": datetime.utcnow().isoformat() 
                }

            # All events valid, process batch 
            background_tasks.add_task( 
                process_event_batch.delay, 
                enriched_events 
            ) 
            logger.info(f"Batch of {len(batch.events)} events ingested successfully", extra={ 
                "batch_size": len(batch.events), 
                "api_key": api_key[:8] + "..." 
            })
            return { 
                "status": "accepted", 
                "batch_size": len(batch.events), 
                "message": "Batch queued for processing", 
                "timestamp": datetime.utcnow().isoformat() 
            } 
    except HTTPException: 
        raise 
    except Exception as e: 
        logger.error(f"Error ingesting batch: {e}", exc_info=True) 
        raise HTTPException(status_code=500, detail="Internal server error")
         
@router.post("/batch", response_model=dict, status_code=202) 
async def ingest_event_batch( 
    request: Request, 
    batch: EventBatch, 
    background_tasks: BackgroundTasks,
    api_key: str = Depends(validate_api_key), 
    redis: RedisClient = Depends(get_redis)  
):
    """ Ingest a batch of analytics events (up to 1000 events per batch) 
    - **events**: List of events to ingest 
    - **api_key**: API key for authentication 
    """ 
    try: 
        # Update rate limiter with redis client 
        rate_limiter.redis = redis 
        # Validate batch size 
        if len(batch.events) > 1000: 
            raise HTTPException( 
                status_code=400, 
                detail="Batch size cannot exceed 1000 events" 
            )
        # Check rate limit (count each event in batch) 
        await rate_limiter.check_limit(api_key, count=len(batch.events))
        
       # Validate and enrich each event 
        enriched_events = [] 
        validation_errors = []

    for i, event in enumerate(batch.events): 
        # Validate event 
        validation_result = validate_event_data(event.dict()) 
        if not validation_result["valid"]: 
            validation_errors.append({ 
                "index": i, 
                "event_id": str(event.event_id), 
                "errors": validation_result["errors"] 
            }) 
            continue
            
        # Enrich event 
        enriched = await enrich_event_data( 
            event.dict(), 
            client_ip=request.client.host if request.client else None, 
            user_agent=request.headers.get("user-agent"), 
            headers=dict(request.headers) 
        ) 
        enriched_events.append(enriched)
        
    # If there were validation errors, return partial success
    if validation_errors:
        if not enriched_events:
             raise HTTPException(
                status_code=400,
                detail={"message": "All events failed validation", "errors": validation_errors}
            )
            
        # Process valid events
         background_tasks.add_task(
            process_event_batch.delay,
            enriched_events
        )
        return {
                "status": "partial_success",
                "accepted_count": len(enriched_events),
                "failed_count": len(validation_errors),
                "errors": validation_errors,
                "timestamp": datetime.utcnow().isoformat()
            }
        
        # All events valid, process batch
        background_tasks.add_task(
            process_event_batch.delay,
            enriched_events
        )
        logger.info(f"Batch of {len(batch.events)} events ingested successfully", extra={ 
            "batch_size": len(batch.events), 
            "api_key": api_key[:8] + "..." 
        })
