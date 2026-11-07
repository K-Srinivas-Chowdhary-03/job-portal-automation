from typing import List
import httpx
from bs4 import BeautifulSoup
from urllib.parse import urljoin
from app.scrapers.base import BaseScraper, ScrapedItem


class GenericHtmlScraper(BaseScraper):
    """Static HTML scraper using HTTPX and BeautifulSoup."""

    async def validate_source(self) -> bool:
        try:
            async with httpx.AsyncClient(headers=self.headers, timeout=15.0, follow_redirects=True) as client:
                res = await client.get(self.source_url)
                return res.status_code == 200
        except Exception:
            return False

    async def collect_raw_jobs(self) -> List[ScrapedItem]:
        items: List[ScrapedItem] = []
        async with httpx.AsyncClient(headers=self.headers, timeout=25.0, follow_redirects=True) as client:
            res = await client.get(self.source_url)
            if res.status_code != 200:
                raise RuntimeError(f"Source returned HTTP {res.status_code}")

            soup = BeautifulSoup(res.text, "html.parser")

            # Check if RSS / XML feed
            if "xml" in res.headers.get("content-type", "") or soup.find("channel"):
                for entry in soup.find_all(["item", "entry"]):
                    title_tag = entry.find(["title"])
                    link_tag = entry.find(["link"])
                    desc_tag = entry.find(["description", "summary", "content"])
                    guid_tag = entry.find(["guid", "id"])

                    title = title_tag.get_text(strip=True) if title_tag else "Notification"
                    link = link_tag.get_text(strip=True) if link_tag else self.source_url
                    if link_tag and link_tag.get("href"):
                        link = link_tag["href"]
                    desc = desc_tag.get_text(strip=True) if desc_tag else ""
                    ext_id = guid_tag.get_text(strip=True) if guid_tag else link

                    items.append(
                        ScrapedItem(
                            external_id=ext_id,
                            title=title,
                            raw_html=str(entry),
                            text_content=f"{title}\n{desc}",
                            source_url=link,
                            metadata={"type": "rss"},
                        )
                    )
                return items

            # HTML Career Page Parsing (using configurable selectors or heuristic fallbacks)
            card_selector = self.config.get("job_card_selector", ".job-card, .career-item, article, li.job")
            title_selector = self.config.get("title_selector", "h2, h3, a.title, .job-title")
            link_selector = self.config.get("link_selector", "a")

            cards = soup.select(card_selector)
            if not cards:
                # Heuristic: search all anchors with 'job', 'career', or 'vacancy' in href
                for a in soup.find_all("a", href=True):
                    href = a["href"]
                    if any(kw in href.lower() for kw in ["/job", "/career", "/vacancy", "/recruitment"]):
                        title = a.get_text(strip=True)
                        if len(title) > 5:
                            full_url = urljoin(self.source_url, href)
                            items.append(
                                ScrapedItem(
                                    external_id=full_url,
                                    title=title,
                                    raw_html=str(a.parent),
                                    text_content=title,
                                    source_url=full_url,
                                    metadata={"heuristic": True},
                                )
                            )
                return items[:30]

            for card in cards:
                title_elem = card.select_one(title_selector)
                link_elem = card.select_one(link_selector)
                title = title_elem.get_text(strip=True) if title_elem else "Open Vacancy"
                href = link_elem["href"] if link_elem and link_elem.has_attr("href") else self.source_url
                full_url = urljoin(self.source_url, href)
                text = card.get_text(separator="\n", strip=True)

                items.append(
                    ScrapedItem(
                        external_id=full_url,
                        title=title,
                        raw_html=str(card),
                        text_content=text,
                        source_url=full_url,
                        metadata={},
                    )
                )

        return items
