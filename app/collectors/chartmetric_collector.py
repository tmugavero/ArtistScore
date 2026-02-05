import aiohttp
from typing import Optional
from datetime import datetime

from app.models.chartmetric import ChartmetricMetrics, ChartmetricStats
from app.models.base import CollectorStatus
from .base import BaseCollector


class ChartmetricCollector(BaseCollector[ChartmetricMetrics]):
    """Collects Chartmetric analytics data."""

    BASE_URL = "https://api.chartmetric.com/api"

    def __init__(self, refresh_token: str, timeout: int = 30):
        super().__init__(timeout)
        self.refresh_token = refresh_token
        self._access_token: Optional[str] = None

    async def _get_access_token(self) -> Optional[str]:
        """Get JWT access token using refresh token."""
        if self._access_token:
            return self._access_token

        url = f"{self.BASE_URL}/token"
        payload = {"refreshtoken": self.refresh_token}

        async with aiohttp.ClientSession() as session:
            async with session.post(url, json=payload, timeout=self.timeout) as resp:
                if resp.status != 200:
                    return None
                data = await resp.json()
                self._access_token = data.get("token")
                return self._access_token

    async def search_artist(self, artist_name: str) -> Optional[dict]:
        """Search for artist in Chartmetric. Returns full search result dict."""
        token = await self._get_access_token()
        if not token:
            return None

        url = f"{self.BASE_URL}/search"
        headers = {"Authorization": f"Bearer {token}"}
        params = {"q": artist_name, "type": "artists", "limit": 1}

        async with aiohttp.ClientSession() as session:
            async with session.get(url, headers=headers, params=params, timeout=self.timeout) as resp:
                if resp.status != 200:
                    return None
                data = await resp.json()
                artists = data.get("obj", {}).get("artists", [])
                if artists:
                    return artists[0]  # Return full dict with all data
                return None

    async def _get_artist_stats(self, artist_id: int) -> Optional[dict]:
        """Get artist statistics from Chartmetric."""
        token = await self._get_access_token()
        if not token:
            return None

        url = f"{self.BASE_URL}/artist/{artist_id}"
        headers = {"Authorization": f"Bearer {token}"}

        async with aiohttp.ClientSession() as session:
            async with session.get(url, headers=headers, timeout=self.timeout) as resp:
                if resp.status != 200:
                    return None
                data = await resp.json()
                return data.get("obj")

    async def _get_spotify_stats(self, artist_id: int) -> Optional[dict]:
        """Get Spotify-specific stats from Chartmetric."""
        token = await self._get_access_token()
        if not token:
            return None

        url = f"{self.BASE_URL}/artist/{artist_id}/stat/spotify"
        headers = {"Authorization": f"Bearer {token}"}

        async with aiohttp.ClientSession() as session:
            async with session.get(url, headers=headers, timeout=self.timeout) as resp:
                if resp.status != 200:
                    return None
                data = await resp.json()
                return data.get("obj")

    async def collect(self, artist_name: str) -> ChartmetricMetrics:
        """Collect Chartmetric data for artist."""
        # Get access token
        token = await self._get_access_token()
        if not token:
            return ChartmetricMetrics(
                status=CollectorStatus.FAILED,
                error_message="Could not authenticate with Chartmetric API",
            )

        # Search for artist - returns full data dict
        search_result = await self.search_artist(artist_name)
        if not search_result:
            return ChartmetricMetrics(
                status=CollectorStatus.FAILED,
                error_message=f"Could not find Chartmetric artist for {artist_name}",
            )

        artist_id = search_result.get("id")

        # Get additional artist data for rank
        artist_data = await self._get_artist_stats(artist_id)

        # Extract data from search results (has more data than detail endpoint)
        sp_followers = search_result.get("sp_followers")
        sp_monthly_listeners = search_result.get("sp_monthly_listeners")
        cm_artist_score = search_result.get("cm_artist_score")

        # Get rank from detail endpoint
        cm_artist_rank = artist_data.get("cm_artist_rank") if artist_data else None

        artist_stats = ChartmetricStats(
            cm_artist_id=artist_id,
            cm_artist_rank=cm_artist_rank,
            cm_artist_score=cm_artist_score,
            sp_followers=sp_followers,
            sp_monthly_listeners=sp_monthly_listeners,
        )

        return ChartmetricMetrics(
            status=CollectorStatus.SUCCESS,
            artist_id=artist_id,
            artist_name=search_result.get("name", artist_name),
            artist_stats=artist_stats,
        )

    def _create_failed_result(self, error_message: str) -> ChartmetricMetrics:
        return ChartmetricMetrics(
            status=CollectorStatus.FAILED,
            error_message=error_message,
        )
