from abc import ABC, abstractmethod
from typing import TypeVar, Generic, Optional

from app.models.base import BaseCollectorResult, CollectorStatus

T = TypeVar('T', bound=BaseCollectorResult)


class BaseCollector(ABC, Generic[T]):
    """Abstract base class for all data collectors."""

    def __init__(self, timeout: int = 30):
        self.timeout = timeout

    @abstractmethod
    async def search_artist(self, artist_name: str) -> Optional[str]:
        """Find artist ID from name. Returns None if not found."""
        pass

    @abstractmethod
    async def collect(self, artist_name: str) -> T:
        """Collect and return normalized metrics."""
        pass

    @abstractmethod
    def _create_failed_result(self, error_message: str) -> T:
        """Create a failed result object."""
        pass

    async def safe_collect(self, artist_name: str) -> T:
        """Wrapper with error handling for graceful degradation."""
        try:
            return await self.collect(artist_name)
        except Exception as e:
            return self._create_failed_result(str(e))
