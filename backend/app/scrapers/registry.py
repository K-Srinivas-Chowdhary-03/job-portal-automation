from typing import Type, Dict, Any
from app.scrapers.base import BaseScraper
from app.scrapers.static.generic_html import GenericHtmlScraper
from app.scrapers.dynamic.generic_playwright import GenericPlaywrightScraper

SCRAPER_REGISTRY: Dict[str, Type[BaseScraper]] = {
    "HTML": GenericHtmlScraper,
    "RSS": GenericHtmlScraper,
    "API": GenericHtmlScraper,
    "PLAYWRIGHT": GenericPlaywrightScraper,
}


def get_scraper_for_source(scraper_type: str, source_url: str, config: Dict[str, Any] = None) -> BaseScraper:
    """Factory function returning the instantiated scraper for a given source type."""
    scraper_cls = SCRAPER_REGISTRY.get(scraper_type.upper(), GenericHtmlScraper)
    return scraper_cls(source_url=source_url, config=config)
