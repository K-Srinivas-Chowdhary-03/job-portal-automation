from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional
import logging
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class ScrapedItem:
    """Represents an extracted raw item before AI normalization."""
    external_id: Optional[str]
    title: str
    raw_html: str
    text_content: str
    source_url: str
    metadata: Dict[str, Any]


class BaseScraper(ABC):
    """Abstract Base Class for all Job Source Scrapers."""

    def __init__(self, source_url: str, config: Optional[Dict[str, Any]] = None):
        self.source_url = source_url
        self.config = config or {}
        self.headers = {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/124.0.0.0 Safari/537.36 JobPortalBot/1.0"
            ),
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.9",
        }

    @abstractmethod
    async def validate_source(self) -> bool:
        """Verify that the target source URL is reachable and accessible."""
        pass

    @abstractmethod
    async def collect_raw_jobs(self) -> List[ScrapedItem]:
        """Fetch and extract raw job items from the target source."""
        pass
