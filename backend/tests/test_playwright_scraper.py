
"""
Playwright scraper tests.

These tests use a local temporary HTTP server.
They do not require external websites, Grok API calls,
or production database records.
"""

import http.server
import socket
import threading
import time
from pathlib import Path
from urllib.parse import urljoin

import pytest

from app.scrapers.dynamic.generic_playwright import GenericPlaywrightScraper


# ---------------------------------------------------------
# Local HTTP server
# ---------------------------------------------------------

class QuietHandler(http.server.SimpleHTTPRequestHandler):

    def log_message(self, *args, **kwargs):
        pass


def start_http_server(root: Path, port: int):

    handler = lambda *args, **kwargs: QuietHandler(
        *args,
        directory=str(root),
        **kwargs
    )

    server = http.server.HTTPServer(
        ("127.0.0.1", port),
        handler
    )

    thread = threading.Thread(
        target=server.serve_forever,
        daemon=True
    )

    thread.start()
    server._thread = thread

    return server


def wait_for_port(port: int, timeout: float = 2.0):

    deadline = time.monotonic() + timeout

    while time.monotonic() < deadline:

        try:
            with socket.create_connection(
                ("127.0.0.1", port),
                timeout=0.1
            ):
                return

        except OSError:
            time.sleep(0.05)

    raise RuntimeError(
        f"Server on port {port} did not become ready"
    )


# ---------------------------------------------------------
# Pytest fixture
# ---------------------------------------------------------

@pytest.fixture(scope="session")
def http_server(tmp_path_factory):

    root = tmp_path_factory.mktemp("playwright_server")

    # HTML page containing two job cards
    (root / "jobs.html").write_text(
        """
        <html>
        <body>
            <ul>
                <li class="job-card">
                    <h2>Senior Engineer</h2>
                    <a href="/job/1">Details</a>
                </li>

                <li class="job-card">
                    <h3>Junior Analyst</h3>
                    <a href="/job/2">Details</a>
                </li>
            </ul>
        </body>
        </html>
        """,
        encoding="utf-8"
    )

    # Empty HTML page
    (root / "empty.html").write_text(
        """
        <html>
        <body>
            <p>No jobs here.</p>
        </body>
        </html>
        """,
        encoding="utf-8"
    )

    # Select an available port
    with socket.socket(
        socket.AF_INET,
        socket.SOCK_STREAM
    ) as s:

        s.bind(("127.0.0.1", 0))
        port = s.getsockname()[1]

    server = start_http_server(root, port)

    wait_for_port(port)

    base_url = f"http://127.0.0.1:{port}"

    yield {
        "base": base_url,
        "root": root,
        "server": server
    }

    # Stop the HTTP server
    server.shutdown()
    server.server_close()
    server._thread.join()


# ---------------------------------------------------------
# Test 1: Successful job extraction
# ---------------------------------------------------------

@pytest.mark.asyncio
async def test_collect_raw_jobs_success(http_server):

    url = f"{http_server['base']}/jobs.html"

    scraper = GenericPlaywrightScraper(
        source_url=url,
        config={}
    )

    items = await scraper.collect_raw_jobs()

    assert len(items) == 2

    titles = {item.title for item in items}

    assert "Senior Engineer" in titles
    assert "Junior Analyst" in titles

    expected_urls = {
        urljoin(url, "/job/1"),
        urljoin(url, "/job/2")
    }

    returned_urls = {
        item.external_id for item in items
    }

    assert returned_urls == expected_urls

    for item in items:
        assert item.metadata.get("browser") == "playwright"


# ---------------------------------------------------------
# Test 2: Empty page
# ---------------------------------------------------------

@pytest.mark.asyncio
async def test_collect_raw_jobs_empty_page(http_server):

    url = f"{http_server['base']}/empty.html"

    scraper = GenericPlaywrightScraper(
        source_url=url,
        config={}
    )

    items = await scraper.collect_raw_jobs()

    assert items == []


# ---------------------------------------------------------
# Test 3: Navigation timeout handling
# ---------------------------------------------------------

@pytest.mark.asyncio
async def test_collect_raw_jobs_navigation_timeout(
    http_server,
    monkeypatch
):

    from playwright.async_api import Error

    async def raise_timeout(*args, **kwargs):

        raise Error("Timeout 30000ms exceeded")

    monkeypatch.setattr(
        "playwright.async_api.Page.goto",
        raise_timeout,
        raising=False
    )

    url = f"{http_server['base']}/jobs.html"

    scraper = GenericPlaywrightScraper(
        source_url=url,
        config={}
    )

    with pytest.raises(Error) as excinfo:
        await scraper.collect_raw_jobs()

    assert "Timeout" in str(excinfo.value)


# ---------------------------------------------------------
# Test 4: Invalid Chromium executable path
# ---------------------------------------------------------

def test_get_chromium_executable_invalid_path(monkeypatch):

    from app.utils.playwright_path import get_chromium_executable

    monkeypatch.setenv(
        "PLAYWRIGHT_EXECUTABLE_PATH",
        "/nonexistent/chrome"
    )

    with pytest.raises(FileNotFoundError):
        get_chromium_executable()


# ---------------------------------------------------------
# Test 5: Navigation error propagation with mocked browser
# ---------------------------------------------------------

@pytest.mark.asyncio
async def test_browser_error_propagation(monkeypatch):

    from playwright.async_api import Error

    class FakePage:

        async def goto(self, *args, **kwargs):
            raise Error("Forced failure for test")

    class FakeContext:

        async def new_page(self):
            return FakePage()

    class FakeBrowser:

        async def new_context(self, *args, **kwargs):
            return FakeContext()

        async def close(self):
            pass

    async def fake_launch(*args, **kwargs):
        return FakeBrowser()

    class FakePlaywright:

        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            pass

        chromium = type(
            "Chromium",
            (),
            {"launch": fake_launch}
        )

    def fake_async_playwright():
        return FakePlaywright()

    monkeypatch.setattr(
        "app.scrapers.dynamic.generic_playwright.async_playwright",
        fake_async_playwright
    )

    scraper = GenericPlaywrightScraper(
        source_url="http://example.invalid",
        config={}
    )

    with pytest.raises(Error):
        await scraper.collect_raw_jobs()
