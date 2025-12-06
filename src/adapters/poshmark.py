"""Poshmark marketplace adapter."""

import asyncio
import logging
from typing import AsyncIterator
from urllib.parse import quote_plus

from playwright.async_api import Page
from playwright.async_api import TimeoutError as PlaywrightTimeout

from src.adapters.base import MarketplaceAdapter
from src.models import Listing

logger = logging.getLogger(__name__)

# Retry configuration
MAX_RETRIES = 3
RETRY_BASE_DELAY = 1.0  # seconds


class PoshmarkAdapter(MarketplaceAdapter):
    """Adapter for searching Poshmark.com - fashion resale marketplace."""

    BASE_URL = "https://poshmark.com"
    NAME = "poshmark"

    SELECTORS = {
        "listing": ".card, .tile, [data-et-name='listing']",
        "title": ".tile__title, .card__title, [data-et-name='title']",
        "price": ".tile__price, .card__price, [data-et-name='price']",
        "link": "a[href*='/listing/']",
        "image": ".tile__image img, .card__image img",
        "no_results": ".no-results, .empty-state",
    }

    async def search(self, page: Page, queries: list[str]) -> AsyncIterator[Listing]:
        """Search Poshmark and yield listings."""
        for query in queries:
            logger.info(f"Searching Poshmark for: {query}")

            try:
                # Navigate to search results - filter to Jewelry category
                search_url = (
                    f"{self.BASE_URL}/search"
                    f"?query={quote_plus(query)}"
                    f"&department=Women&category=Jewelry&subcategory=Rings"
                )
                await page.goto(search_url, wait_until="domcontentloaded")
                await self._rate_limit()

                # Wait for dynamic content to load
                await page.wait_for_timeout(2000)

                # Check for no results
                no_results = await page.query_selector(self.SELECTORS["no_results"])
                if no_results:
                    logger.info(f"No results for query: {query}")
                    continue

                # Process current page
                async for listing in self._extract_listings(page):
                    yield listing

            except PlaywrightTimeout:
                logger.warning(f"Timeout searching Poshmark for: {query}")
            except Exception as e:
                logger.error(f"Error searching Poshmark: {e}")

    async def _extract_listings(self, page: Page) -> AsyncIterator[Listing]:
        """Extract listings from current page using batch JavaScript extraction.

        Uses page.evaluate() to extract all listing data in a single JS call,
        avoiding stale element handle errors from DOM changes during iteration.
        """
        try:
            await page.wait_for_selector(self.SELECTORS["listing"], timeout=10000)
        except PlaywrightTimeout:
            logger.warning("No listings found on page")
            return

        # Extract all listings in a single JavaScript call to avoid stale handles
        listings_data = await page.evaluate(
            """
            (selectors) => {
                const results = [];
                const listings = document.querySelectorAll(selectors.listing);

                listings.forEach(element => {
                    try {
                        // Extract link
                        let linkElement = element.querySelector(selectors.link);
                        if (!linkElement) {
                            linkElement = element.querySelector('a');
                        }
                        if (!linkElement) return;

                        const href = linkElement.getAttribute('href');
                        if (!href || !href.includes('/listing/')) return;

                        // Extract title
                        const titleElement = element.querySelector(selectors.title);
                        const title = titleElement ? titleElement.textContent.trim() : '';

                        // Extract price
                        const priceElement = element.querySelector(selectors.price);
                        const price = priceElement ? priceElement.textContent.trim() : null;

                        // Extract image URL
                        const imageElement = element.querySelector(selectors.image);
                        const imageUrl = imageElement ? imageElement.getAttribute('src') : null;

                        results.push({
                            href: href,
                            title: title,
                            price: price,
                            imageUrl: imageUrl
                        });
                    } catch (e) {
                        // Skip problematic elements
                    }
                });

                return results;
            }
            """,
            self.SELECTORS,
        )

        for data in listings_data:
            try:
                href = data.get("href", "")
                url = href if href.startswith("http") else f"{self.BASE_URL}{href}"

                yield Listing(
                    url=url,
                    source=self.NAME,
                    title=data.get("title", ""),
                    price=data.get("price"),
                    description=None,
                    image_url=data.get("imageUrl"),
                )
            except Exception as e:
                logger.warning(f"Error processing listing data: {e}")

    async def get_listing_details(self, page: Page, url: str) -> Listing | None:
        """Get detailed information for a specific listing with retry logic.

        Uses page.evaluate() for batch extraction and exponential backoff
        for transient failures.
        """
        last_error: Exception | None = None

        for attempt in range(MAX_RETRIES):
            try:
                await page.goto(url, wait_until="domcontentloaded")
                await self._rate_limit()

                # Wait for dynamic content
                await page.wait_for_timeout(2000)

                # Extract all details in a single JavaScript call
                details = await page.evaluate(
                    """
                    () => {
                        const titleEl = document.querySelector(
                            '.listing__title, h1[data-et-name="title"]'
                        );
                        const priceEl = document.querySelector(
                            '.listing__price, [data-et-name="price"]'
                        );
                        const descEl = document.querySelector(
                            '.listing__description, [data-et-name="description"]'
                        );
                        const imageEl = document.querySelector(
                            '.listing__image img, .carousel img'
                        );

                        return {
                            title: titleEl ? titleEl.textContent.trim() : '',
                            price: priceEl ? priceEl.textContent.trim() : null,
                            description: descEl
                                ? descEl.textContent.trim().substring(0, 500)
                                : null,
                            imageUrl: imageEl ? imageEl.getAttribute('src') : null
                        };
                    }
                    """
                )

                return Listing(
                    url=url,
                    source=self.NAME,
                    title=details.get("title", ""),
                    price=details.get("price"),
                    description=details.get("description"),
                    image_url=details.get("imageUrl"),
                )

            except PlaywrightTimeout as e:
                last_error = e
                if attempt < MAX_RETRIES - 1:
                    delay = RETRY_BASE_DELAY * (2**attempt)
                    logger.warning(
                        f"Timeout fetching Poshmark details (attempt {attempt + 1}/{MAX_RETRIES}), "
                        f"retrying in {delay:.1f}s: {url}"
                    )
                    await asyncio.sleep(delay)
            except Exception as e:
                last_error = e
                if attempt < MAX_RETRIES - 1:
                    delay = RETRY_BASE_DELAY * (2**attempt)
                    logger.warning(
                        f"Error fetching Poshmark details (attempt {attempt + 1}/{MAX_RETRIES}), "
                        f"retrying in {delay:.1f}s: {e}"
                    )
                    await asyncio.sleep(delay)

        logger.error(f"Failed to fetch Poshmark listing after {MAX_RETRIES} attempts: {last_error}")
        return None
