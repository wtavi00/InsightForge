from datetime import datetime, timedelta
from typing import Optional, Union, Dict, Any
from jose import JWTError, jwt
from passlib.context import CryptContext
from fastapi import HTTPException, Security, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials, APIKeyHeader
from fastapi.websockets import WebSocket
from app.core.config import settings
import secrets
import logging
import uuid

logger = logging.getLogger(__name__)

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

security = HTTPBearer()
api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a plain password against a hashed password"""
    return pwd_context.verify(plain_password, hashed_password)
