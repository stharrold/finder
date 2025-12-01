"""Etsy marketplace adapter."""

import logging
from typing import AsyncIterator
from urllib.parse import quote_plus, urljoin

from playwright.async_api import Page
from playwright.async_api import TimeoutError as PlaywrightTimeout

from src.adapters.base import MarketplaceAdapter
from src.models import Listing

logger = logging.getLogger(__name__)


class EtsyAdapter(MarketplaceAdapter):
    """Adapter for searching Etsy.com."""

    BASE_URL = "https://www.etsy.com"
    NAME = "etsy"

    SELECTORS = {
        "listing": ".v2-listing-card, [data-listing-card]",
        "title": ".v2-listing-card__title, [data-listing-title]",
        "price": ".currency-value, .lc-price",
        "link": "a.listing-link, a[href*='/listing/']",
        "image": ".v2-listing-card__img img, [data-listing-card] img",
        "next_page": "[aria-label='Next page'], .pagination-link-next",
        "no_results": ".wt-alert, .no-results",
    }

    async def search(self, page: Page, queries: list[str]) -> AsyncIterator[Listing]:
        """Search Etsy and yield listings.

        Args:
            page: Playwright page instance.
            queries: List of search query strings.

        Yields:
            Listing objects for each result found.
        """
        for query in queries:
            logger.info(f"Searching Etsy for: {query}")

            try:
                # Navigate to search results
                search_url = f"{self.BASE_URL}/search?q={quote_plus(query)}"
                await page.goto(search_url, wait_until="domcontentloaded")
                await self._rate_limit()

                # Check for no results
                no_results = await page.query_selector(self.SELECTORS["no_results"])
                if no_results:
                    no_results_text = await no_results.text_content() or ""
                    if "no results" in no_results_text.lower():
                        logger.info(f"No results for query: {query}")
                        continue

                # Process current page
                async for listing in self._extract_listings(page):
                    yield listing

                # Handle pagination (up to 3 pages per query)
                for page_num in range(2, 4):
                    if not await self._has_next_page(page):
                        break

                    await self._go_to_next_page(page)
                    await self._rate_limit()

                    async for listing in self._extract_listings(page):
                        yield listing

            except PlaywrightTimeout:
                logger.warning(f"Timeout searching Etsy for: {query}")
            except Exception as e:
                logger.error(f"Error searching Etsy: {e}")

    async def _extract_listings(self, page: Page) -> AsyncIterator[Listing]:
        """Extract listings from current page."""
        try:
            await page.wait_for_selector(self.SELECTORS["listing"], timeout=10000)
        except PlaywrightTimeout:
            logger.warning("No listings found on page")
            return

        listing_elements = await page.query_selector_all(self.SELECTORS["listing"])

        for element in listing_elements:
            try:
                # Extract link
                link_element = await element.query_selector(self.SELECTORS["link"])
                if not link_element:
                    continue

                href = await link_element.get_attribute("href")
                if not href or "/listing/" not in href:
                    continue

                # Clean URL - remove tracking params
                url = href.split("?")[0]
                if not url.startswith("http"):
                    url = urljoin(self.BASE_URL, url)

                # Extract title
                title_element = await element.query_selector(self.SELECTORS["title"])
                title = ""
                if title_element:
                    title = await title_element.text_content() or ""
                    title = title.strip()

                if not title:
                    # Fallback: try alt text from image
                    img_element = await element.query_selector(self.SELECTORS["image"])
                    if img_element:
                        title = await img_element.get_attribute("alt") or ""
                        title = title.strip()

                # Extract price
                price_element = await element.query_selector(self.SELECTORS["price"])
                price = None
                if price_element:
                    price = await price_element.text_content()
                    if price:
                        price = price.strip()

                # Extract image URL
                image_element = await element.query_selector(self.SELECTORS["image"])
                image_url = None
                if image_element:
                    image_url = await image_element.get_attribute("src")

                yield Listing(
                    url=url,
                    source=self.NAME,
                    title=title,
                    price=price,
                    description=None,
                    image_url=image_url,
                )

            except Exception as e:
                logger.warning(f"Error extracting listing: {e}")

    async def _has_next_page(self, page: Page) -> bool:
        """Check if there's a next page of results."""
        next_button = await page.query_selector(self.SELECTORS["next_page"])
        if not next_button:
            return False

        is_disabled = await next_button.get_attribute("disabled")
        return is_disabled is None

    async def _go_to_next_page(self, page: Page) -> None:
        """Navigate to the next page of results."""
        next_button = await page.query_selector(self.SELECTORS["next_page"])
        if next_button:
            await next_button.click()
            await page.wait_for_load_state("domcontentloaded")

    async def get_listing_details(self, page: Page, url: str) -> Listing | None:
        """Get detailed information for a specific listing."""
        try:
            await page.goto(url, wait_until="domcontentloaded")
            await self._rate_limit()

            # Extract title
            title_element = await page.query_selector("h1, [data-listing-title]")
            title = ""
            if title_element:
                title = await title_element.text_content() or ""
                title = title.strip()

            # Extract price
            price_element = await page.query_selector(".wt-text-title-03, [data-buy-box-region] .currency-value")
            price = None
            if price_element:
                price = await price_element.text_content()
                if price:
                    price = price.strip()

            # Extract description
            desc_element = await page.query_selector(
                "[data-product-details-description-text-content], .wt-content-toggle__body"
            )
            description = None
            if desc_element:
                description = await desc_element.text_content()
                if description:
                    description = description.strip()[:500]

            # Extract image
            image_element = await page.query_selector(
                "[data-listing-page-image] img, .listing-page-image-container img"
            )
            image_url = None
            if image_element:
                image_url = await image_element.get_attribute("src")

            return Listing(
                url=url,
                source=self.NAME,
                title=title,
                price=price,
                description=description,
                image_url=image_url,
            )

        except Exception as e:
            logger.error(f"Error fetching Etsy listing details: {e}")
            return None
