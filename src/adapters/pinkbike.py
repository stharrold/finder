"""Pinkbike marketplace adapter for bike listings."""

import logging
from typing import AsyncIterator
from urllib.parse import quote_plus

from playwright.async_api import Page
from playwright.async_api import TimeoutError as PlaywrightTimeout

from src.adapters.base import MarketplaceAdapter
from src.models import Listing

logger = logging.getLogger(__name__)


class PinkbikeAdapter(MarketplaceAdapter):
    """Adapter for searching Pinkbike Buy/Sell marketplace."""

    BASE_URL = "https://www.pinkbike.com"
    NAME = "pinkbike"

    SELECTORS = {
        "listing": ".buysell-item, .bsitem, [data-type='buysell']",
        "title": ".buysell-title, .bsitem-title, h2 a",
        "price": ".buysell-price, .bsitem-price, .price",
        "link": "a.buysell-title, .bsitem-title a, h2 a",
        "image": ".buysell-image img, .bsitem-image img, .thumb img",
        "location": ".buysell-location, .bsitem-location, .location",
        "no_results": ".no-results, .empty-state",
        "next_page": ".pagination .next, a[rel='next']",
    }

    # E-bike category on Pinkbike
    CATEGORY_EBIKE = 75

    async def search(self, page: Page, queries: list[str]) -> AsyncIterator[Listing]:
        """Search Pinkbike Buy/Sell and yield listings.

        Args:
            page: Playwright page instance.
            queries: List of search query strings.

        Yields:
            Listing objects for each result found.
        """
        for query in queries:
            logger.info(f"Searching Pinkbike for: {query}")

            try:
                # Navigate to buy/sell search - filter to e-bikes category
                # Pinkbike URL format: /buysell/?q=query&category=75
                search_url = (
                    f"{self.BASE_URL}/buysell/"
                    f"?q={quote_plus(query)}"
                    f"&category={self.CATEGORY_EBIKE}"
                    f"&region=3"  # North America region
                )
                await page.goto(search_url, wait_until="domcontentloaded")
                await self._rate_limit()

                # Check for no results
                no_results = await page.query_selector(self.SELECTORS["no_results"])
                if no_results:
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
                logger.warning(f"Timeout searching Pinkbike for: {query}")
            except Exception as e:
                logger.error(f"Error searching Pinkbike: {e}")

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
                if not href:
                    continue

                # Ensure full URL
                url = href if href.startswith("http") else f"{self.BASE_URL}{href}"

                # Extract title
                title_element = await element.query_selector(self.SELECTORS["title"])
                title = ""
                if title_element:
                    title = await title_element.text_content() or ""
                    title = title.strip()

                if not title:
                    continue

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

                # Extract location for filtering
                location_element = await element.query_selector(self.SELECTORS["location"])
                location = None
                if location_element:
                    location = await location_element.text_content()
                    if location:
                        location = location.strip()

                # Include location in description if available
                description = f"Location: {location}" if location else None

                yield Listing(
                    url=url,
                    source=self.NAME,
                    title=title,
                    price=price,
                    description=description,
                    image_url=image_url,
                )

            except Exception as e:
                logger.warning(f"Error extracting listing: {e}")

    async def _has_next_page(self, page: Page) -> bool:
        """Check if there's a next page of results."""
        next_button = await page.query_selector(self.SELECTORS["next_page"])
        return next_button is not None

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
            title_element = await page.query_selector("h1.buysell-title, h1")
            title = ""
            if title_element:
                title = await title_element.text_content() or ""
                title = title.strip()

            # Extract price
            price_element = await page.query_selector(".buysell-price, .price")
            price = None
            if price_element:
                price = await price_element.text_content()
                if price:
                    price = price.strip()

            # Extract description
            desc_element = await page.query_selector(".buysell-description, .description, .item-description")
            description = None
            if desc_element:
                description = await desc_element.text_content()
                if description:
                    description = description.strip()[:1000]  # Limit length

            # Extract specs if available
            specs_element = await page.query_selector(".buysell-specs, .specs")
            if specs_element:
                specs_text = await specs_element.text_content()
                if specs_text:
                    if description:
                        description = f"{description}\n\nSpecs: {specs_text.strip()}"
                    else:
                        description = f"Specs: {specs_text.strip()}"

            # Extract image
            image_element = await page.query_selector(".buysell-image img, .main-image img, .gallery img")
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
            logger.error(f"Error fetching Pinkbike listing details: {e}")
            return None
