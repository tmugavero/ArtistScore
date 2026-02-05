from pydantic import BaseModel
from typing import Optional, List
from .base import BaseCollectorResult


class NewsArticle(BaseModel):
    """A news article from Brave Search."""
    title: str
    url: str
    description: Optional[str] = None
    source: str
    age: Optional[str] = None  # e.g., "2 days ago"


class BraveSearchMetrics(BaseCollectorResult):
    """Brave Search metrics for web presence."""
    news_articles: List[NewsArticle] = []
    total_results_count: int = 0
    recent_news_count: int = 0  # Articles from recent searches
