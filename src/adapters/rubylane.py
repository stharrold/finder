"""Ruby Lane marketplace adapter."""

import logging
from typing import AsyncIterator
from urllib.parse import quote_plus

from playwright.async_api import Page
from playwright.async_api import TimeoutError as PlaywrightTimeout

from src.adapters.base import MarketplaceAdapter
from src.models import Listing

logger = logging.getLogger(__name__)


class RubyLaneAdapter(MarketplaceAdapter):
    """Adapter for searching RubyLane.com - antiques and vintage marketplace."""

    BASE_URL = "https://www.rubylane.com"
    NAME = "rubylane"

    SELECTORS = {
        "listing": ".item-card, .search-result-item, [data-item-id]",
        "title": ".item-title, .item-card-title, h3 a",
        "price": ".item-price, .price",
        "link": "a[href*='/item/'], .item-card a",
        "image": ".item-image img, .item-card img",
        "no_results": ".no-results, .empty-results",
    }

    async def search(self, page: Page, queries: list[str]) -> AsyncIterator[Listing]:
        """Search Ruby Lane and yield listings."""
        for query in queries:
            logger.info(f"Searching Ruby Lane for: {query}")

            try:
                # Navigate to search results - filter to Jewelry category
                search_url = f"{self.BASE_URL}/search?q={quote_plus(query)}&cat=jewelry"
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

            except PlaywrightTimeout:
                logger.warning(f"Timeout searching Ruby Lane for: {query}")
            except Exception as e:
                logger.error(f"Error searching Ruby Lane: {e}")

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
                    link_element = await element.query_selector("a")
                if not link_element:
                    continue

                href = await link_element.get_attribute("href")
                if not href:
                    continue

                url = href if href.startswith("http") else f"{self.BASE_URL}{href}"

                # Extract title
                title_element = await element.query_selector(self.SELECTORS["title"])
                title = ""
                if title_element:
                    title = await title_element.text_content() or ""
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

    async def get_listing_details(self, page: Page, url: str) -> Listing | None:
        """Get detailed information for a specific listing."""
        try:
            await page.goto(url, wait_until="domcontentloaded")
            await self._rate_limit()

            # Extract title
            title_element = await page.query_selector("h1, .item-title")
            title = ""
            if title_element:
                title = await title_element.text_content() or ""
                title = title.strip()

            # Extract price
            price_element = await page.query_selector(".item-price, .price")
            price = None
            if price_element:
                price = await price_element.text_content()
                if price:
                    price = price.strip()

            # Extract description
            desc_element = await page.query_selector(".item-description, .description")
            description = None
            if desc_element:
                description = await desc_element.text_content()
                if description:
                    description = description.strip()[:500]

            # Extract image
            image_element = await page.query_selector(".item-image img, .main-image img")
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
            logger.error(f"Error fetching Ruby Lane listing details: {e}")
            return None
