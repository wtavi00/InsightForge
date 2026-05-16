import logging
import sys
from typing import Dict, Any
from pythonjsonlogger import jsonlogger
from app.core.config import settings
import structlog

def setup_logging():
    """Configure logging for the application"""
    log_level = logging.DEBUG if settings.DEBUG else logging.INFO
    root_logger = logging.getLogger()
    root_logger.setLevel(log_level)
    root_logger.handlers.clear()
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(log_level)
    if settings.DEBUG:
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
    else:
        # JSON - production
        formatter = jsonlogger.JsonFormatter(
            '%(asctime)s %(name)s %(levelname)s %(message)s %(pathname)s %(lineno)d',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
    console_handler.setFormatter(formatter)
    root_logger.addHandler(console_handler)

    structlog.configure(
        processors=[
            structlog.stdlib.filter_by_level,
            structlog.stdlib.add_logger_name,
            structlog.stdlib.add_log_level,
            structlog.stdlib.PositionalArgumentsFormatter(),
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            structlog.processors.UnicodeDecoder(),
            structlog.stdlib.ProcessorFormatter.wrap_for_formatter,
        ],
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )

    # Set specific log levels for noisy libraries
    logging.getLogger("uvicorn").setLevel(logging.WARNING)
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)
    logging.getLogger("aioredis").setLevel(logging.WARNING)
    logging.getLogger("celery").setLevel(logging.INFO)
    
    # Log startup
    logging.info(f"Logging configured - Environment: {'development' if settings.DEBUG else 'production'}")

class RequestLogger:
    """Middleware for logging requests"""
    
    @staticmethod
    def log_request(request, response=None, error=None):
        """Log request details"""
        logger = logging.getLogger("access")
        
        log_data = {
            "method": request.method,
            "path": request.url.path,
            "query_params": str(request.query_params),
            "client_host": request.client.host if request.client else None,
            "user_agent": request.headers.get("user-agent"),
            "request_id": request.headers.get("X-Request-ID"),
        }
    
if response:

            log_data.update({

                "status_code": response.status_code,

                "response_time": getattr(response, "response_time", None),

            })

        
        if error:

            log_data.update({

                "error": str(error),

                "error_type": 
    type(error).__name__,

            })

            logger.error("Request failed", extra=log_data)

        else:

            logger.info("Request completed", extra=log_data)


