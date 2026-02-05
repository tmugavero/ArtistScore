from google import genai
from typing import List
import json
import re

from app.models.sentiment import SentimentCategory, AggregatedSentiment
from app.models.brave import NewsArticle


class SentimentAnalyzer:
    """Gemini-powered sentiment analysis for artist news coverage."""

    def __init__(self, api_key: str):
        self.client = genai.Client(api_key=api_key)
        self.model_name = "gemini-2.0-flash"

    def _format_articles(self, articles: List[NewsArticle]) -> str:
        """Format articles for the prompt."""
        formatted = []
        for i, article in enumerate(articles[:10], 1):  # Limit to 10 articles
            formatted.append(
                f"{i}. Title: {article.title}\n"
                f"   Source: {article.source}\n"
                f"   Description: {article.description or 'N/A'}"
            )
        return "\n\n".join(formatted)

    def _build_prompt(self, artist_name: str, articles_text: str) -> str:
        """Build the analysis prompt for Gemini."""
        return f"""Analyze the sentiment of the following news articles about the music artist "{artist_name}".

Articles:
{articles_text}

Provide your analysis in the following JSON format only (no markdown, no code blocks):
{{
    "overall_sentiment": "very_positive" or "positive" or "neutral" or "negative" or "very_negative",
    "sentiment_score": <float from -1.0 to 1.0, where -1 is very negative and 1 is very positive>,
    "confidence": <float from 0.0 to 1.0>,
    "key_themes": ["theme1", "theme2", "theme3"],
    "summary": "A 2-3 sentence summary of the artist's public perception based on these articles",
    "brand_safety_concerns": ["concern1", "concern2"] or []
}}

Consider:
- Overall tone of coverage (positive achievements vs negative incidents)
- Controversies or legal issues mentioned
- Career achievements and milestones highlighted
- Brand safety for potential partnerships
- Recent activity and relevance

Return ONLY the JSON object, no additional text."""

    def _parse_response(self, response_text: str) -> dict:
        """Parse the JSON response from Gemini."""
        # Try to extract JSON from the response
        try:
            # Remove markdown code blocks if present
            text = response_text.strip()
            if text.startswith("```"):
                text = re.sub(r"```json?\s*", "", text)
                text = re.sub(r"```\s*$", "", text)

            return json.loads(text)
        except json.JSONDecodeError:
            # Return default values if parsing fails
            return {
                "overall_sentiment": "neutral",
                "sentiment_score": 0.0,
                "confidence": 0.5,
                "key_themes": [],
                "summary": "Unable to analyze sentiment from available data.",
                "brand_safety_concerns": [],
            }

    def _map_sentiment_category(self, sentiment_str: str) -> SentimentCategory:
        """Map string sentiment to category enum."""
        mapping = {
            "very_positive": SentimentCategory.VERY_POSITIVE,
            "positive": SentimentCategory.POSITIVE,
            "neutral": SentimentCategory.NEUTRAL,
            "negative": SentimentCategory.NEGATIVE,
            "very_negative": SentimentCategory.VERY_NEGATIVE,
        }
        return mapping.get(sentiment_str.lower(), SentimentCategory.NEUTRAL)

    async def analyze_articles(
        self,
        artist_name: str,
        articles: List[NewsArticle],
    ) -> AggregatedSentiment:
        """Analyze sentiment across news articles using Gemini."""
        if not articles:
            return AggregatedSentiment(
                overall_category=SentimentCategory.NEUTRAL,
                overall_score=0.0,
                confidence=0.3,
                sample_size=0,
                key_themes=[],
                summary=f"No recent news articles found for {artist_name}. Unable to assess public sentiment.",
                brand_safety_concerns=[],
            )

        # Format articles and build prompt
        articles_text = self._format_articles(articles)
        prompt = self._build_prompt(artist_name, articles_text)

        try:
            # Generate analysis
            response = self.client.models.generate_content(
                model=self.model_name,
                contents=prompt,
            )
            parsed = self._parse_response(response.text)

            return AggregatedSentiment(
                overall_category=self._map_sentiment_category(parsed.get("overall_sentiment", "neutral")),
                overall_score=float(parsed.get("sentiment_score", 0.0)),
                confidence=float(parsed.get("confidence", 0.5)),
                sample_size=len(articles),
                key_themes=parsed.get("key_themes", []),
                summary=parsed.get("summary", "Analysis completed."),
                brand_safety_concerns=parsed.get("brand_safety_concerns", []),
            )
        except Exception as e:
            return AggregatedSentiment(
                overall_category=SentimentCategory.NEUTRAL,
                overall_score=0.0,
                confidence=0.2,
                sample_size=len(articles),
                key_themes=[],
                summary=f"Error analyzing sentiment: {str(e)}",
                brand_safety_concerns=[],
            )

    async def generate_artist_summary(
        self,
        artist_name: str,
        scores: dict,
        sentiment: AggregatedSentiment,
    ) -> str:
        """Generate an AI summary of the artist's brand value."""
        prompt = f"""Based on the following data about music artist "{artist_name}", write a 2-3 sentence executive summary for brand partnership consideration:

Scores (0-100 scale):
- Spotify Score: {scores.get('spotify', 'N/A')}
- YouTube Score: {scores.get('youtube', 'N/A')}
- Chartmetric Score: {scores.get('chartmetric', 'N/A')}
- Web Presence Score: {scores.get('web_presence', 'N/A')}
- Sentiment Score: {scores.get('sentiment', 'N/A')}

Sentiment Analysis:
- Overall: {sentiment.overall_category.value}
- Key Themes: {', '.join(sentiment.key_themes) if sentiment.key_themes else 'None identified'}
- Brand Safety Concerns: {', '.join(sentiment.brand_safety_concerns) if sentiment.brand_safety_concerns else 'None identified'}

Write a professional summary highlighting:
1. Overall brand value assessment
2. Key strengths for brand partnerships
3. Any considerations or concerns

Keep it concise and professional, suitable for a brand marketing team."""

        try:
            response = self.client.models.generate_content(
                model=self.model_name,
                contents=prompt,
            )
            return response.text.strip()
        except Exception:
            return f"{artist_name} shows {'strong' if scores.get('spotify', 0) > 70 else 'moderate'} potential for brand partnerships based on available metrics."
