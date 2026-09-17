from fastapi import APIRouter, Depends, HTTPException, Query 
from typing import Optional, List, Dict, Any 
from datetime import datetime, timedelta 
from sqlalchemy.ext.asyncio import AsyncSession 
import json 
import logging
