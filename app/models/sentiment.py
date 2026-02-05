from pydantic import BaseModel
from typing import List
from enum import Enum


class SentimentCategory(str, Enum):
    """Sentiment classification categories."""
    VERY_POSITIVE = "very_positive"
    POSITIVE = "positive"
    NEUTRAL = "neutral"
    NEGATIVE = "negative"
    VERY_NEGATIVE = "very_negative"


class AggregatedSentiment(BaseModel):
    """Aggregated sentiment analysis results."""
    overall_category: SentimentCategory
    overall_score: float  # -1.0 to 1.0
    confidence: float  # 0.0 to 1.0
    sample_size: int
    key_themes: List[str] = []
    summary: str
    brand_safety_concerns: List[str] = []
