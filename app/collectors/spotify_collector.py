import spotipy
from spotipy.oauth2 import SpotifyClientCredentials
from typing import Optional
import asyncio
from functools import partial

from app.models.spotify import SpotifyMetrics, SpotifyArtistStats
from app.models.base import CollectorStatus
from .base import BaseCollector


class SpotifyCollector(BaseCollector[SpotifyMetrics]):
    """Collects Spotify artist metrics."""

    def __init__(self, client_id: str, client_secret: str, timeout: int = 30):
        super().__init__(timeout)
        self.sp = None
        self._init_error = None
        try:
            self.sp = spotipy.Spotify(
                auth_manager=SpotifyClientCredentials(
                    client_id=client_id,
                    client_secret=client_secret,
                )
            )
        except Exception as e:
            self._init_error = str(e)

    async def search_artist(self, artist_name: str) -> Optional[str]:
        """Search for artist on Spotify."""
        if not self.sp:
            return None
        loop = asyncio.get_event_loop()
        try:
            result = await loop.run_in_executor(
                None,
                partial(self.sp.search, q=artist_name, type="artist", limit=1),
            )
            artists = result.get("artists", {}).get("items", [])
            if artists:
                return artists[0]["id"]
            return None
        except Exception:
            return None

    async def _get_artist(self, artist_id: str) -> Optional[dict]:
        """Get artist details."""
        loop = asyncio.get_event_loop()
        try:
            return await loop.run_in_executor(
                None,
                partial(self.sp.artist, artist_id),
            )
        except Exception:
            return None

    async def _get_top_tracks(self, artist_id: str) -> list:
        """Get artist's top tracks."""
        loop = asyncio.get_event_loop()
        try:
            result = await loop.run_in_executor(
                None,
                partial(self.sp.artist_top_tracks, artist_id),
            )
            return result.get("tracks", [])
        except Exception:
            return []

    async def collect(self, artist_name: str) -> SpotifyMetrics:
        """Collect Spotify metrics for artist."""
        # Check for initialization errors
        if not self.sp:
            return SpotifyMetrics(
                status=CollectorStatus.FAILED,
                error_message=f"Spotify API not initialized: {self._init_error or 'Invalid credentials'}",
            )

        # Search for artist
        artist_id = await self.search_artist(artist_name)
        if not artist_id:
            return SpotifyMetrics(
                status=CollectorStatus.FAILED,
                error_message=f"Could not find Spotify artist for {artist_name}",
            )

        # Get artist details
        artist_data = await self._get_artist(artist_id)
        if not artist_data:
            return SpotifyMetrics(
                status=CollectorStatus.PARTIAL,
                artist_id=artist_id,
                error_message="Could not retrieve artist details",
            )

        followers = artist_data.get("followers", {}).get("total", 0)
        popularity = artist_data.get("popularity", 0)
        genres = artist_data.get("genres", [])
        name = artist_data.get("name", artist_name)

        artist_stats = SpotifyArtistStats(
            followers=followers,
            popularity=popularity,
            genres=genres,
        )

        # Get top tracks for average popularity
        top_tracks = await self._get_top_tracks(artist_id)
        top_tracks_avg = 0.0
        if top_tracks:
            total_pop = sum(t.get("popularity", 0) for t in top_tracks)
            top_tracks_avg = total_pop / len(top_tracks)

        return SpotifyMetrics(
            status=CollectorStatus.SUCCESS,
            artist_id=artist_id,
            artist_name=name,
            artist_stats=artist_stats,
            top_tracks_avg_popularity=top_tracks_avg,
        )

    def _create_failed_result(self, error_message: str) -> SpotifyMetrics:
        return SpotifyMetrics(
            status=CollectorStatus.FAILED,
            error_message=error_message,
        )
