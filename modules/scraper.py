"""
modules/scraper.py — Job listing scraper using Playwright + BeautifulSoup.

Supports multiple job boards via config-driven CSS selectors.
Auto-detects which board selector profile to use based on the URL hostname.
"""

import logging
import time
import random
from urllib.parse import urlparse
from bs4 import BeautifulSoup
from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeout

import config

logger = logging.getLogger(__name__)

# Rotate user-agents to reduce bot-detection risk
_USER_AGENTS = [
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_4) AppleWebKit/605.1.15 "
    "(KHTML, like Gecko) Version/17.4 Safari/605.1.15",
]


def _get_selectors(url: str) -> dict[str, str]:
    """
    Returns the CSS selector profile for the given URL by matching its
    hostname against BOARD_SELECTORS in config. Falls back to 'default'.
    """
    hostname = urlparse(url).netloc.lower()
    for board_key, selectors in config.BOARD_SELECTORS.items():
        if board_key != "default" and board_key in hostname:
            logger.debug(f"Matched board profile '{board_key}' for {hostname}")
            return selectors
    logger.debug(f"No board match for {hostname}, using default selectors.")
    return config.BOARD_SELECTORS["default"]


def _safe_get_text(soup: BeautifulSoup, selector: str, label: str) -> str:
    """
    Attempts to extract text from a CSS selector.
    Logs a warning and returns an empty string if not found.
    """
    element = soup.select_one(selector)
    if element:
        return element.get_text(separator=" ", strip=True)
    logger.warning(f"Selector not found for '{label}': {selector!r}")
    return ""


def scrape_job_listing(url: str) -> dict | None:
    """
    Scrapes a single job listing URL using Playwright (headless Chrome)
    and BeautifulSoup for HTML parsing.

    Returns a dict with keys: title, company, description, url, board
    Returns None if scraping fails.
    """
    selectors = _get_selectors(url)
    board = urlparse(url).netloc

    user_agent = random.choice(_USER_AGENTS)
    logger.info(f"Scraping: {url}")

    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=config.PLAYWRIGHT_HEADLESS)
            context = browser.new_context(
                user_agent=user_agent,
                locale="en-US",
                viewport={"width": 1280, "height": 800},
                extra_http_headers={
                    "Accept-Language": "en-US,en;q=0.9",
                    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                },
            )
            page = context.new_page()

            # Random polite delay to avoid rate limiting
            time.sleep(random.uniform(1.5, 3.5))

            page.goto(url, timeout=config.PLAYWRIGHT_TIMEOUT_MS, wait_until="networkidle")

            # Extra wait for JS-heavy pages
            page.wait_for_timeout(2000)

            html = page.content()
            browser.close()

    except PlaywrightTimeout:
        logger.error(f"Timeout loading page: {url}")
        return None
    except Exception as exc:
        logger.error(f"Playwright error for {url}: {exc}")
        return None

    soup = BeautifulSoup(html, "lxml")

    title       = _safe_get_text(soup, selectors["title"],       "title")
    company     = _safe_get_text(soup, selectors["company"],     "company")
    description = _safe_get_text(soup, selectors["description"], "description")

    if not title and not company:
        logger.warning(f"Could not extract title or company from {url}. "
                       "Consider updating selectors in config.py.")

    result = {
        "title":       title       or "Unknown Title",
        "company":     company     or "Unknown Company",
        "description": description or "",
        "url":         url,
        "board":       board,
    }

    logger.info(f"Scraped: '{result['title']}' at '{result['company']}'")
    return result
