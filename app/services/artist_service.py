import asyncio
from typing import Optional

from app.collectors.youtube_collector import YouTubeCollector
from app.collectors.spotify_collector import SpotifyCollector
from app.collectors.chartmetric_collector import ChartmetricCollector
from app.collectors.brave_collector import BraveSearchCollector
from app.analyzers.sentiment_analyzer import SentimentAnalyzer
from app.analyzers.score_calculator import ScoreCalculator
from app.models.score import ArtistScoreResponse
from app.models.youtube import YouTubeMetrics
from app.models.spotify import SpotifyMetrics
from app.models.chartmetric import ChartmetricMetrics
from app.models.brave import BraveSearchMetrics
from app.models.base import CollectorStatus
from app.config import Settings


class ArtistScoringService:
    """Main orchestration service for artist scoring."""

    def __init__(self, settings: Settings):
        self.youtube = YouTubeCollector(settings.YOUTUBE_API)
        self.spotify = SpotifyCollector(
            settings.SPOTIFY_API,
            settings.SPOTIFY_SECRET,
        )
        self.chartmetric = ChartmetricCollector(settings.CHARTMETRIC)
        self.brave = BraveSearchCollector(settings.BRAVE_API)
        self.sentiment_analyzer = SentimentAnalyzer(settings.GEMINI_API)
        self.calculator = ScoreCalculator()

    def _handle_exception(self, result, source: str):
        """Convert exceptions to failed collector results."""
        if isinstance(result, Exception):
            error_msg = str(result)
            if source == "youtube":
                return YouTubeMetrics(
                    status=CollectorStatus.FAILED,
                    error_message=f"YouTube collection failed: {error_msg}",
                )
            elif source == "spotify":
                return SpotifyMetrics(
                    status=CollectorStatus.FAILED,
                    error_message=f"Spotify collection failed: {error_msg}",
                )
            elif source == "chartmetric":
                return ChartmetricMetrics(
                    status=CollectorStatus.FAILED,
                    error_message=f"Chartmetric collection failed: {error_msg}",
                )
            elif source == "brave":
                return BraveSearchMetrics(
                    status=CollectorStatus.FAILED,
                    error_message=f"Brave search failed: {error_msg}",
                    news_articles=[],
                    total_results_count=0,
                    recent_news_count=0,
                )
        return result

    async def get_artist_score(
        self,
        artist_name: str,
        include_details: bool = True,
    ) -> ArtistScoreResponse:
        """
        Main entry point for scoring an artist.
        Runs all collectors in parallel for performance.
        """
        # Run all collectors in parallel
        results = await asyncio.gather(
            self.youtube.safe_collect(artist_name),
            self.spotify.safe_collect(artist_name),
            self.chartmetric.safe_collect(artist_name),
            self.brave.safe_collect(artist_name),
            return_exceptions=True,
        )

        # Handle any exceptions from gather
        youtube_data = self._handle_exception(results[0], "youtube")
        spotify_data = self._handle_exception(results[1], "spotify")
        chartmetric_data = self._handle_exception(results[2], "chartmetric")
        brave_data = self._handle_exception(results[3], "brave")

        # Run sentiment analysis on collected news
        sentiment_data = await self.sentiment_analyzer.analyze_articles(
            artist_name,
            brave_data.news_articles if brave_data and hasattr(brave_data, "news_articles") else [],
        )

        # Generate AI summary if details requested
        ai_summary = ""
        if include_details:
            scores = {
                "spotify": self.calculator._calculate_spotify_score(spotify_data).normalized_score,
                "youtube": self.calculator._calculate_youtube_score(youtube_data).normalized_score,
                "chartmetric": self.calculator._calculate_chartmetric_score(chartmetric_data).normalized_score,
                "web_presence": self.calculator._calculate_web_presence_score(brave_data).normalized_score,
                "sentiment": self.calculator._calculate_sentiment_score(sentiment_data).normalized_score,
            }
            ai_summary = await self.sentiment_analyzer.generate_artist_summary(
                artist_name, scores, sentiment_data
            )

        # Calculate final score
        return self.calculator.calculate_final_score(
            artist_name=artist_name,
            spotify=spotify_data,
            youtube=youtube_data,
            chartmetric=chartmetric_data,
            brave=brave_data,
            sentiment=sentiment_data,
            ai_summary=ai_summary,
        )
