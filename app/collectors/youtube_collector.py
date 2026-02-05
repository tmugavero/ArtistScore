import aiohttp
from typing import Optional
from datetime import datetime

from app.models.youtube import YouTubeMetrics, YouTubeChannelStats
from app.models.base import CollectorStatus
from .base import BaseCollector


class YouTubeCollector(BaseCollector[YouTubeMetrics]):
    """Collects YouTube channel and video statistics."""

    BASE_URL = "https://www.googleapis.com/youtube/v3"

    def __init__(self, api_key: str, timeout: int = 30):
        super().__init__(timeout)
        self.api_key = api_key

    async def search_artist(self, artist_name: str) -> Optional[str]:
        """Search for artist's YouTube channel with multiple query strategies."""
        search_url = f"{self.BASE_URL}/search"

        # Try different search queries to find the artist's channel
        search_queries = [
            f"{artist_name} official artist channel",
            f"{artist_name} VEVO",
            f"{artist_name} official",
            f"{artist_name} music",
            artist_name,
        ]

        candidate_channels = []

        async with aiohttp.ClientSession() as session:
            for query in search_queries:
                params = {
                    "part": "snippet",
                    "q": query,
                    "type": "channel",
                    "maxResults": 10,
                    "key": self.api_key,
                }

                async with session.get(search_url, params=params, timeout=self.timeout) as resp:
                    if resp.status != 200:
                        continue
                    data = await resp.json()
                    items = data.get("items", [])

                    for item in items:
                        channel_id = item["id"]["channelId"]
                        title = item.get("snippet", {}).get("title", "")
                        # Only consider channels that contain the artist name
                        if artist_name.lower() in title.lower():
                            if channel_id not in [c[0] for c in candidate_channels]:
                                candidate_channels.append((channel_id, title))

            # If we found candidates, get their subscriber counts and pick the largest
            if candidate_channels:
                best_channel = None
                best_subs = 0

                for channel_id, title in candidate_channels[:5]:  # Check top 5 candidates
                    stats = await self._get_channel_stats(channel_id)
                    if stats:
                        subs = int(stats.get("statistics", {}).get("subscriberCount", 0))
                        if subs > best_subs:
                            best_subs = subs
                            best_channel = channel_id

                if best_channel:
                    return best_channel

            # Fallback: return first result from any search
            for query in search_queries[:2]:
                params = {
                    "part": "snippet",
                    "q": query,
                    "type": "channel",
                    "maxResults": 1,
                    "key": self.api_key,
                }
                async with session.get(search_url, params=params, timeout=self.timeout) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        items = data.get("items", [])
                        if items:
                            return items[0]["id"]["channelId"]

        return None

    async def _get_channel_stats(self, channel_id: str) -> Optional[dict]:
        """Get channel statistics."""
        url = f"{self.BASE_URL}/channels"
        params = {
            "part": "statistics,snippet",
            "id": channel_id,
            "key": self.api_key,
        }

        async with aiohttp.ClientSession() as session:
            async with session.get(url, params=params, timeout=self.timeout) as resp:
                if resp.status != 200:
                    return None
                data = await resp.json()
                items = data.get("items", [])
                if items:
                    return items[0]
                return None

    async def _get_recent_videos(self, channel_id: str, max_results: int = 10) -> list:
        """Get recent videos from channel."""
        search_url = f"{self.BASE_URL}/search"
        params = {
            "part": "snippet",
            "channelId": channel_id,
            "type": "video",
            "order": "date",
            "maxResults": max_results,
            "key": self.api_key,
        }

        async with aiohttp.ClientSession() as session:
            async with session.get(search_url, params=params, timeout=self.timeout) as resp:
                if resp.status != 200:
                    return []
                data = await resp.json()
                return data.get("items", [])

    async def _get_video_stats(self, video_ids: list) -> dict:
        """Get statistics for multiple videos."""
        if not video_ids:
            return {}

        url = f"{self.BASE_URL}/videos"
        params = {
            "part": "statistics",
            "id": ",".join(video_ids),
            "key": self.api_key,
        }

        async with aiohttp.ClientSession() as session:
            async with session.get(url, params=params, timeout=self.timeout) as resp:
                if resp.status != 200:
                    return {}
                data = await resp.json()
                return {item["id"]: item["statistics"] for item in data.get("items", [])}

    async def collect(self, artist_name: str) -> YouTubeMetrics:
        """Collect YouTube metrics for artist."""
        # Search for channel
        channel_id = await self.search_artist(artist_name)
        if not channel_id:
            return YouTubeMetrics(
                status=CollectorStatus.FAILED,
                error_message=f"Could not find YouTube channel for {artist_name}",
            )

        # Get channel stats
        channel_data = await self._get_channel_stats(channel_id)
        if not channel_data:
            return YouTubeMetrics(
                status=CollectorStatus.PARTIAL,
                channel_id=channel_id,
                error_message="Could not retrieve channel statistics",
            )

        stats = channel_data.get("statistics", {})
        snippet = channel_data.get("snippet", {})

        subscriber_count = int(stats.get("subscriberCount", 0))
        view_count = int(stats.get("viewCount", 0))
        video_count = int(stats.get("videoCount", 1))

        avg_views = view_count / max(video_count, 1)

        # Get recent videos for engagement calculation
        recent_videos = await self._get_recent_videos(channel_id)
        video_ids = [v["id"]["videoId"] for v in recent_videos if "videoId" in v.get("id", {})]
        video_stats = await self._get_video_stats(video_ids)

        recent_avg_views = 0.0
        if video_stats:
            total_views = sum(int(s.get("viewCount", 0)) for s in video_stats.values())
            recent_avg_views = total_views / len(video_stats)

        # Estimate engagement rate
        engagement_rate = min(recent_avg_views / max(subscriber_count, 1) * 100, 100)

        channel_stats = YouTubeChannelStats(
            subscriber_count=subscriber_count,
            view_count=view_count,
            video_count=video_count,
            avg_views_per_video=avg_views,
            engagement_rate=engagement_rate,
        )

        return YouTubeMetrics(
            status=CollectorStatus.SUCCESS,
            channel_id=channel_id,
            channel_name=snippet.get("title", ""),
            channel_stats=channel_stats,
            recent_video_avg_views=recent_avg_views,
        )

    def _create_failed_result(self, error_message: str) -> YouTubeMetrics:
        return YouTubeMetrics(
            status=CollectorStatus.FAILED,
            error_message=error_message,
        )
