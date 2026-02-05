from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime


class ScoreComponent(BaseModel):
    """Individual score component breakdown."""
    name: str
    weight: float
    raw_value: Optional[float] = None
    normalized_score: float  # 0-100
    status: str
    reasoning: str


class ScoreBreakdown(BaseModel):
    """Complete breakdown of all score components."""
    spotify_score: ScoreComponent
    youtube_score: ScoreComponent
    chartmetric_score: ScoreComponent
    web_presence_score: ScoreComponent
    sentiment_score: ScoreComponent


class SentimentOverview(BaseModel):
    """Sentiment analysis overview for brand safety."""
    overall_sentiment: str
    sentiment_score: float  # -1.0 to 1.0
    confidence: float
    key_themes: List[str] = []
    brand_safety_concerns: List[str] = []
    sample_size: int


class ArtistScoreResponse(BaseModel):
    """Final artist score response."""
    artist_name: str
    final_score: float = Field(..., ge=0, le=100)
    score_grade: str  # A+, A, B+, B, C+, C, D, F
    breakdown: ScoreBreakdown
    sentiment_overview: SentimentOverview
    key_strengths: List[str]
    areas_for_improvement: List[str]
    ai_summary: str
    data_freshness: datetime
    confidence_level: float  # 0-1 based on data availability
    warnings: List[str] = []
