import logging
import sys
from typing import Dict, Any
from pythonjsonlogger import jsonlogger
from app.core.config import settings
import structlog

def setup_logging():
    """Configure logging for the application"""
    
    # Set log level based on debug mode
    log_level = logging.DEBUG if settings.DEBUG else logging.INFO
    
    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(log_level)
    
    # Remove existing handlers
    root_logger.handlers.clear()
    
    # Create console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(log_level)
    
