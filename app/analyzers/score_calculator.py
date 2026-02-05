import math
from typing import Dict, List, Tuple, Optional

from app.models.score import ScoreComponent, ScoreBreakdown, ArtistScoreResponse
from app.models.spotify import SpotifyMetrics
from app.models.youtube import YouTubeMetrics
from app.models.chartmetric import ChartmetricMetrics
from app.models.brave import BraveSearchMetrics
from app.models.sentiment import AggregatedSentiment, SentimentCategory
from app.models.base import CollectorStatus
from datetime import datetime


class ScoreCalculator:
    """Calculates weighted artist score from all data sources."""

    WEIGHTS = {
        "spotify": 0.35,
        "youtube": 0.30,
        "chartmetric": 0.25,
        "sentiment": 0.07,
        "web_presence": 0.03,
    }

    # Thresholds for log-scale normalization
    SUBSCRIBER_THRESHOLDS = {
        "min": 1000,
        "mid": 100000,
        "max": 50000000,
    }

    FOLLOWER_THRESHOLDS = {
        "min": 5000,
        "mid": 500000,
        "max": 200000000,  # 200M to account for mega-artists
    }

    VIEW_THRESHOLDS = {
        "min": 10000,
        "mid": 1000000,
        "max": 100000000,
    }

    NEWS_THRESHOLDS = {
        "min": 1,
        "mid": 10,
        "max": 50,
    }

    def _log_normalize(self, value: float, min_val: float, max_val: float) -> float:
        """Normalize using logarithmic scale."""
        if value <= min_val:
            return 0.0
        if value >= max_val:
            return 100.0

        log_value = math.log10(value)
        log_min = math.log10(min_val)
        log_max = math.log10(max_val)

        return ((log_value - log_min) / (log_max - log_min)) * 100

    def _linear_normalize(self, value: float, min_val: float, max_val: float) -> float:
        """Simple linear normalization to 0-100 scale."""
        if value <= min_val:
            return 0.0
        if value >= max_val:
            return 100.0
        return ((value - min_val) / (max_val - min_val)) * 100

    def _calculate_spotify_score(self, data: SpotifyMetrics) -> ScoreComponent:
        """Calculate Spotify component score."""
        if data.status == CollectorStatus.FAILED or not data.artist_stats:
            return ScoreComponent(
                name="Spotify",
                weight=self.WEIGHTS["spotify"],
                normalized_score=0,
                status="failed",
                reasoning=data.error_message or "Unable to retrieve Spotify data",
            )

        stats = data.artist_stats

        # Popularity is already 0-100 (60% weight)
        popularity_component = stats.popularity * 0.60

        # Followers on log scale (40% weight)
        follower_score = self._log_normalize(
            stats.followers,
            self.FOLLOWER_THRESHOLDS["min"],
            self.FOLLOWER_THRESHOLDS["max"],
        )
        follower_component = follower_score * 0.40

        total = popularity_component + follower_component

        return ScoreComponent(
            name="Spotify",
            weight=self.WEIGHTS["spotify"],
            raw_value=float(stats.popularity),
            normalized_score=min(total, 100),
            status="success",
            reasoning=f"Popularity: {stats.popularity}/100, Followers: {stats.followers:,}",
        )

    def _calculate_youtube_score(self, data: YouTubeMetrics) -> ScoreComponent:
        """Calculate YouTube component score."""
        if data.status == CollectorStatus.FAILED or not data.channel_stats:
            return ScoreComponent(
                name="YouTube",
                weight=self.WEIGHTS["youtube"],
                normalized_score=0,
                status="failed",
                reasoning=data.error_message or "Unable to retrieve YouTube data",
            )

        stats = data.channel_stats

        # Subscriber count on log scale (40% weight)
        sub_score = self._log_normalize(
            stats.subscriber_count,
            self.SUBSCRIBER_THRESHOLDS["min"],
            self.SUBSCRIBER_THRESHOLDS["max"],
        )
        sub_component = sub_score * 0.40

        # Average views per video (35% weight)
        view_score = self._log_normalize(
            stats.avg_views_per_video,
            self.VIEW_THRESHOLDS["min"],
            self.VIEW_THRESHOLDS["max"],
        )
        view_component = view_score * 0.35

        # Engagement rate (25% weight) - capped at 100
        engagement_component = min(stats.engagement_rate, 25)

        total = sub_component + view_component + engagement_component

        return ScoreComponent(
            name="YouTube",
            weight=self.WEIGHTS["youtube"],
            raw_value=float(stats.subscriber_count),
            normalized_score=min(total, 100),
            status="success",
            reasoning=f"Subscribers: {stats.subscriber_count:,}, Avg Views: {stats.avg_views_per_video:,.0f}, Engagement: {stats.engagement_rate:.1f}%",
        )

    def _calculate_chartmetric_score(self, data: ChartmetricMetrics) -> ScoreComponent:
        """Calculate Chartmetric component score."""
        if data.status == CollectorStatus.FAILED or not data.artist_stats:
            return ScoreComponent(
                name="Chartmetric",
                weight=self.WEIGHTS["chartmetric"],
                normalized_score=0,
                status="failed",
                reasoning=data.error_message or "Unable to retrieve Chartmetric data",
            )

        stats = data.artist_stats
        components = []
        reasoning_parts = []

        # CM Artist Rank (most important - rank 1 = best)
        if stats.cm_artist_rank:
            # Convert rank to score: rank 1 = 100, rank 100 = 80, rank 1000 = 60, rank 10000 = 40
            if stats.cm_artist_rank <= 10:
                rank_score = 100 - (stats.cm_artist_rank - 1)  # 1->100, 10->91
            elif stats.cm_artist_rank <= 100:
                rank_score = 90 - ((stats.cm_artist_rank - 10) / 90 * 10)  # 10->90, 100->80
            elif stats.cm_artist_rank <= 1000:
                rank_score = 80 - ((stats.cm_artist_rank - 100) / 900 * 20)  # 100->80, 1000->60
            else:
                rank_score = max(60 - ((stats.cm_artist_rank - 1000) / 9000 * 40), 20)
            components.append(rank_score * 0.50)
            reasoning_parts.append(f"Global Rank: #{stats.cm_artist_rank:,}")

        # CM Artist Score (0-100 proprietary score)
        if stats.cm_artist_score:
            components.append(stats.cm_artist_score * 0.30)
            reasoning_parts.append(f"CM Score: {stats.cm_artist_score:.1f}")

        # Monthly listeners as fallback
        if stats.sp_monthly_listeners:
            ml_score = self._log_normalize(
                stats.sp_monthly_listeners,
                10000,  # 10K min
                100000000,  # 100M max
            )
            components.append(ml_score * 0.20)
            reasoning_parts.append(f"Monthly Listeners: {stats.sp_monthly_listeners:,}")

        if not components:
            return ScoreComponent(
                name="Chartmetric",
                weight=self.WEIGHTS["chartmetric"],
                normalized_score=50,
                status="partial",
                reasoning="Limited Chartmetric data available",
            )

        # Calculate weighted total
        total = sum(components)

        return ScoreComponent(
            name="Chartmetric",
            weight=self.WEIGHTS["chartmetric"],
            raw_value=float(stats.cm_artist_rank or 0),
            normalized_score=min(total, 100),
            status="success",
            reasoning=", ".join(reasoning_parts) if reasoning_parts else "Data collected",
        )

    def _calculate_web_presence_score(self, data: BraveSearchMetrics) -> ScoreComponent:
        """Calculate web presence component score."""
        if data.status == CollectorStatus.FAILED:
            return ScoreComponent(
                name="Web Presence",
                weight=self.WEIGHTS["web_presence"],
                normalized_score=0,
                status="failed",
                reasoning=data.error_message or "Unable to retrieve web presence data",
            )

        # Score based on recent news count
        news_score = self._linear_normalize(
            data.recent_news_count,
            self.NEWS_THRESHOLDS["min"],
            self.NEWS_THRESHOLDS["max"],
        )

        return ScoreComponent(
            name="Web Presence",
            weight=self.WEIGHTS["web_presence"],
            raw_value=float(data.recent_news_count),
            normalized_score=news_score,
            status="success" if data.recent_news_count > 0 else "partial",
            reasoning=f"{data.recent_news_count} recent news articles found",
        )

    def _calculate_sentiment_score(self, sentiment: AggregatedSentiment) -> ScoreComponent:
        """Calculate sentiment component score."""
        # Map sentiment score (-1 to 1) to (0 to 100)
        base_score = (sentiment.overall_score + 1) * 50

        # Weight by confidence
        weighted_score = base_score * sentiment.confidence

        # Penalty for brand safety concerns
        concern_penalty = len(sentiment.brand_safety_concerns) * 5
        final_score = max(weighted_score - concern_penalty, 0)

        status = "success" if sentiment.sample_size > 0 else "partial"

        return ScoreComponent(
            name="Sentiment",
            weight=self.WEIGHTS["sentiment"],
            raw_value=sentiment.overall_score,
            normalized_score=min(final_score, 100),
            status=status,
            reasoning=f"{sentiment.overall_category.value.replace('_', ' ').title()}, Confidence: {sentiment.confidence:.0%}, Sample: {sentiment.sample_size} articles",
        )

    def _weighted_average(self, components: Dict[str, ScoreComponent]) -> Tuple[float, float]:
        """Calculate weighted average with graceful degradation."""
        total_score = 0.0
        available_weight = 0.0

        for name, component in components.items():
            if component.status in ("success", "partial"):
                total_score += component.normalized_score * component.weight
                available_weight += component.weight

        if available_weight == 0:
            return 0.0, 0.0

        # Normalize to account for missing data
        final_score = total_score / available_weight
        confidence = available_weight

        return final_score, confidence

    def _score_to_grade(self, score: float) -> str:
        """Convert numeric score to letter grade."""
        if score >= 95:
            return "A+"
        if score >= 90:
            return "A"
        if score >= 85:
            return "B+"
        if score >= 80:
            return "B"
        if score >= 75:
            return "C+"
        if score >= 70:
            return "C"
        if score >= 60:
            return "D"
        return "F"

    def _identify_strengths(self, components: Dict[str, ScoreComponent]) -> List[str]:
        """Identify key strengths from component scores."""
        strengths = []
        for name, component in components.items():
            if component.normalized_score >= 80:
                if name == "spotify":
                    strengths.append(f"Strong Spotify presence ({component.reasoning})")
                elif name == "youtube":
                    strengths.append(f"Excellent YouTube engagement ({component.reasoning})")
                elif name == "chartmetric":
                    strengths.append(f"Strong industry metrics ({component.reasoning})")
                elif name == "sentiment":
                    strengths.append(f"Positive public sentiment ({component.reasoning})")
                elif name == "web_presence":
                    strengths.append(f"High media visibility ({component.reasoning})")
        return strengths if strengths else ["Consistent performance across metrics"]

    def _identify_improvements(self, components: Dict[str, ScoreComponent]) -> List[str]:
        """Identify areas for improvement."""
        improvements = []
        for name, component in components.items():
            if component.status == "failed":
                improvements.append(f"No {name.replace('_', ' ')} data available")
            elif component.normalized_score < 50:
                if name == "spotify":
                    improvements.append("Could benefit from increased Spotify engagement")
                elif name == "youtube":
                    improvements.append("YouTube presence has room for growth")
                elif name == "chartmetric":
                    improvements.append("Chart performance could be improved")
                elif name == "sentiment":
                    improvements.append("Public sentiment could be more positive")
                elif name == "web_presence":
                    improvements.append("Limited recent media coverage")
        return improvements if improvements else ["No significant concerns identified"]

    def calculate_final_score(
        self,
        artist_name: str,
        spotify: SpotifyMetrics,
        youtube: YouTubeMetrics,
        chartmetric: ChartmetricMetrics,
        brave: BraveSearchMetrics,
        sentiment: AggregatedSentiment,
        ai_summary: str = "",
    ) -> ArtistScoreResponse:
        """Calculate final weighted score with full breakdown."""
        components = {
            "spotify": self._calculate_spotify_score(spotify),
            "youtube": self._calculate_youtube_score(youtube),
            "chartmetric": self._calculate_chartmetric_score(chartmetric),
            "web_presence": self._calculate_web_presence_score(brave),
            "sentiment": self._calculate_sentiment_score(sentiment),
        }

        final_score, confidence = self._weighted_average(components)
        grade = self._score_to_grade(final_score)

        # Build warnings
        warnings = []
        for name, component in components.items():
            if component.status == "failed":
                warnings.append(f"{component.name} data unavailable: {component.reasoning}")

        breakdown = ScoreBreakdown(
            spotify_score=components["spotify"],
            youtube_score=components["youtube"],
            chartmetric_score=components["chartmetric"],
            web_presence_score=components["web_presence"],
            sentiment_score=components["sentiment"],
        )

        return ArtistScoreResponse(
            artist_name=artist_name,
            final_score=round(final_score, 1),
            score_grade=grade,
            breakdown=breakdown,
            key_strengths=self._identify_strengths(components),
            areas_for_improvement=self._identify_improvements(components),
            ai_summary=ai_summary or sentiment.summary,
            data_freshness=datetime.utcnow(),
            confidence_level=round(confidence, 2),
            warnings=warnings,
        )
