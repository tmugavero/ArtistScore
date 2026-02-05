from pydantic import BaseModel
from typing import Optional
from .base import BaseCollectorResult


class YouTubeChannelStats(BaseModel):
    """YouTube channel statistics."""
    subscriber_count: int
    view_count: int
    video_count: int
    avg_views_per_video: float
    engagement_rate: float  # Estimated based on views


class YouTubeMetrics(BaseCollectorResult):
    """YouTube metrics for an artist."""
    channel_id: Optional[str] = None
    channel_name: Optional[str] = None
    channel_stats: Optional[YouTubeChannelStats] = None
    recent_video_avg_views: Optional[float] = None
