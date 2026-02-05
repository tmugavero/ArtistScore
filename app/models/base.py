from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime
from enum import Enum


class CollectorStatus(str, Enum):
    """Status of a data collection attempt."""
    SUCCESS = "success"
    PARTIAL = "partial"
    FAILED = "failed"


class BaseCollectorResult(BaseModel):
    """Base class for all collector results."""
    status: CollectorStatus
    collected_at: datetime = Field(default_factory=datetime.utcnow)
    error_message: Optional[str] = None
    raw_score: Optional[float] = None  # 0-100 normalized score
