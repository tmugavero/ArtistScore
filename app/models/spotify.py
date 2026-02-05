from pydantic import BaseModel
from typing import Optional, List
from .base import BaseCollectorResult


class SpotifyArtistStats(BaseModel):
    """Spotify artist statistics."""
    followers: int
    popularity: int  # 0-100 Spotify popularity score
    genres: List[str]


class SpotifyMetrics(BaseCollectorResult):
    """Spotify metrics for an artist."""
    artist_id: Optional[str] = None
    artist_name: Optional[str] = None
    artist_stats: Optional[SpotifyArtistStats] = None
    top_tracks_avg_popularity: Optional[float] = None
