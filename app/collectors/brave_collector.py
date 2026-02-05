import aiohttp
from typing import Optional, List

from app.models.brave import BraveSearchMetrics, NewsArticle
from app.models.base import CollectorStatus
from .base import BaseCollector


class BraveSearchCollector(BaseCollector[BraveSearchMetrics]):
    """Collects web presence data via Brave Search."""

    BASE_URL = "https://api.search.brave.com/res/v1"

    def __init__(self, api_key: str, timeout: int = 30):
        super().__init__(timeout)
        self.api_key = api_key

    async def search_artist(self, artist_name: str) -> Optional[str]:
        """Not needed for Brave - just return the artist name."""
        return artist_name

    async def _search_news(self, query: str, count: int = 20) -> List[NewsArticle]:
        """Search for news articles about the artist."""
        url = f"{self.BASE_URL}/news/search"
        headers = {
            "Accept": "application/json",
            "X-Subscription-Token": self.api_key,
        }
        params = {
            "q": query,
            "count": count,
            "freshness": "pm",  # Past month
        }

        articles = []
        async with aiohttp.ClientSession() as session:
            async with session.get(url, headers=headers, params=params, timeout=self.timeout) as resp:
                if resp.status != 200:
                    return []
                data = await resp.json()

                results = data.get("results", [])
                for item in results:
                    article = NewsArticle(
                        title=item.get("title", ""),
                        url=item.get("url", ""),
                        description=item.get("description"),
                        source=item.get("meta_url", {}).get("hostname", "unknown"),
                        age=item.get("age"),
                    )
                    articles.append(article)

        return articles

    async def _search_web(self, query: str, count: int = 10) -> int:
        """Search web for total result count."""
        url = f"{self.BASE_URL}/web/search"
        headers = {
            "Accept": "application/json",
            "X-Subscription-Token": self.api_key,
        }
        params = {
            "q": query,
            "count": count,
        }

        async with aiohttp.ClientSession() as session:
            async with session.get(url, headers=headers, params=params, timeout=self.timeout) as resp:
                if resp.status != 200:
                    return 0
                data = await resp.json()
                # Get total count from web results
                web_results = data.get("web", {})
                return len(web_results.get("results", []))

    async def collect(self, artist_name: str) -> BraveSearchMetrics:
        """Collect web presence metrics for artist."""
        # Search for news about the artist
        news_query = f"{artist_name} musician artist music"
        news_articles = await self._search_news(news_query)

        # Get general web presence count
        web_count = await self._search_web(f'"{artist_name}" music')

        if not news_articles and web_count == 0:
            return BraveSearchMetrics(
                status=CollectorStatus.PARTIAL,
                news_articles=[],
                total_results_count=0,
                recent_news_count=0,
                error_message=f"Limited web presence found for {artist_name}",
            )

        return BraveSearchMetrics(
            status=CollectorStatus.SUCCESS,
            news_articles=news_articles,
            total_results_count=web_count,
            recent_news_count=len(news_articles),
        )

    def _create_failed_result(self, error_message: str) -> BraveSearchMetrics:
        return BraveSearchMetrics(
            status=CollectorStatus.FAILED,
            error_message=error_message,
            news_articles=[],
            total_results_count=0,
            recent_news_count=0,
        )
