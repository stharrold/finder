"""Mercari marketplace adapter."""

import logging
from typing import AsyncIterator
from urllib.parse import quote_plus

from playwright.async_api import Page
from playwright.async_api import TimeoutError as PlaywrightTimeout

from src.adapters.base import MarketplaceAdapter
from src.models import Listing

logger = logging.getLogger(__name__)


class MercariAdapter(MarketplaceAdapter):
    """Adapter for searching Mercari.com - popular resale marketplace."""

    BASE_URL = "https://www.mercari.com"
    NAME = "mercari"

    SELECTORS = {
        "listing": "[data-testid='ItemContainer'], .sc-bczRLJ",
        "title": "[data-testid='ItemName'], .sc-lkqHmb",
        "price": "[data-testid='ItemPrice'], .sc-cMljjf",
        "link": "a[href*='/item/']",
        "image": "img[src*='static.mercdn.net']",
        "no_results": "[data-testid='SearchNoResults'], .sc-no-results",
    }

    async def search(self, page: Page, queries: list[str]) -> AsyncIterator[Listing]:
        """Search Mercari and yield listings."""
        for query in queries:
            logger.info(f"Searching Mercari for: {query}")

            try:
                # Navigate to search results - filter to Jewelry category
                search_url = (
                    f"{self.BASE_URL}/search"
                    f"?keyword={quote_plus(query)}"
                    f"&categoryIds=29"  # Jewelry category
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
                logger.warning(f"Timeout searching Mercari for: {query}")
            except Exception as e:
                logger.error(f"Error searching Mercari: {e}")

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
                if not href or "/item/" not in href:
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

            # Wait for dynamic content
            await page.wait_for_timeout(2000)

            # Extract title
            title_element = await page.query_selector(
                "[data-testid='ItemName'], h1, .item-name"
            )
            title = ""
            if title_element:
                title = await title_element.text_content() or ""
                title = title.strip()

            # Extract price
            price_element = await page.query_selector(
                "[data-testid='ItemPrice'], .item-price"
            )
            price = None
            if price_element:
                price = await price_element.text_content()
                if price:
                    price = price.strip()

            # Extract description
            desc_element = await page.query_selector(
                "[data-testid='ItemDescription'], .item-description"
            )
            description = None
            if desc_element:
                description = await desc_element.text_content()
                if description:
                    description = description.strip()[:500]

            # Extract image
            image_element = await page.query_selector(
                "[data-testid='ItemImage'] img, .item-photo img"
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
            logger.error(f"Error fetching Mercari listing details: {e}")
            return None
