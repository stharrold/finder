"""Poshmark marketplace adapter."""

import logging
from typing import AsyncIterator
from urllib.parse import quote_plus

from playwright.async_api import Page
from playwright.async_api import TimeoutError as PlaywrightTimeout

from src.adapters.base import MarketplaceAdapter
from src.models import Listing

logger = logging.getLogger(__name__)


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
                if not href or "/listing/" not in href:
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
                ".listing__title, h1[data-et-name='title']"
            )
            title = ""
            if title_element:
                title = await title_element.text_content() or ""
                title = title.strip()

            # Extract price
            price_element = await page.query_selector(
                ".listing__price, [data-et-name='price']"
            )
            price = None
            if price_element:
                price = await price_element.text_content()
                if price:
                    price = price.strip()

            # Extract description
            desc_element = await page.query_selector(
                ".listing__description, [data-et-name='description']"
            )
            description = None
            if desc_element:
                description = await desc_element.text_content()
                if description:
                    description = description.strip()[:500]

            # Extract image
            image_element = await page.query_selector(
                ".listing__image img, .carousel img"
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
            logger.error(f"Error fetching Poshmark listing details: {e}")
            return None
