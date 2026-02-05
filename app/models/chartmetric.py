from pydantic import BaseModel
from typing import Optional, List
from .base import BaseCollectorResult


class ChartmetricStats(BaseModel):
    """Chartmetric artist statistics."""
    cm_artist_id: int
    cm_artist_rank: Optional[int] = None  # Global rank (1 = top artist)
    cm_artist_score: Optional[float] = None  # Chartmetric score
    sp_followers: Optional[int] = None
    sp_popularity: Optional[int] = None
    sp_monthly_listeners: Optional[int] = None


class ChartmetricMetrics(BaseCollectorResult):
    """Chartmetric metrics for an artist."""
    artist_id: Optional[int] = None
    artist_name: Optional[str] = None
    artist_stats: Optional[ChartmetricStats] = None
    chart_count: int = 0  # Number of chart appearances
