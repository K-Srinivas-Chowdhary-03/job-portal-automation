from typing import List
from urllib.parse import urljoin
from app.utils.playwright_path import get_chromium_executable
from app.scrapers.base import BaseScraper, ScrapedItem
from playwright.async_api import async_playwright


class GenericPlaywrightScraper(BaseScraper):
    """Dynamic Playwright scraper for JavaScript-heavy single-page applications."""

    async def validate_source(self) -> bool:
        try:
            async with async_playwright() as p:
                from app.utils.playwright_path import get_chromium_executable
                executable = get_chromium_executable()
                browser = await p.chromium.launch(headless=True, executable_path=executable)
                page = await browser.new_page()
                res = await page.goto(self.source_url, timeout=20000, wait_until="domcontentloaded")
                status = res.status if res else 500
                await browser.close()
                return status < 400
        except Exception:
            return False

    async def collect_raw_jobs(self) -> List[ScrapedItem]:
        items: List[ScrapedItem] = []
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            context = await browser.new_context(user_agent=self.headers["User-Agent"])
            page = await context.new_page()

            await page.goto(self.source_url, timeout=30000, wait_until="networkidle")

            selector = self.config.get("job_card_selector", "[data-testid*='job'], .job-listing, article, li")
            elements = await page.query_selector_all(selector)

            for el in elements[:40]:
                raw_html = await el.inner_html()
                text = await el.inner_text()
                link_elem = await el.query_selector("a")
                href = await link_elem.get_attribute("href") if link_elem else self.source_url
                full_url = urljoin(self.source_url, href or self.source_url)

                title_elem = await el.query_selector("h1, h2, h3, h4, [class*='title']")
                title = (await title_elem.inner_text()) if title_elem else "Career Opportunity"

                items.append(
                    ScrapedItem(
                        external_id=full_url,
                        title=title.strip(),
                        raw_html=raw_html,
                        text_content=text.strip(),
                        source_url=full_url,
                        metadata={"browser": "playwright"},
                    )
                )

            await browser.close()

        return items
