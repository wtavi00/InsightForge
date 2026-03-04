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
