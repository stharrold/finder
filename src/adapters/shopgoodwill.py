"""ShopGoodwill marketplace adapter."""

import logging
from typing import AsyncIterator
from urllib.parse import quote_plus, urljoin

from playwright.async_api import Page
from playwright.async_api import TimeoutError as PlaywrightTimeout

from src.adapters.base import MarketplaceAdapter
from src.models import Listing

logger = logging.getLogger(__name__)


class ShopGoodwillAdapter(MarketplaceAdapter):
    """Adapter for searching ShopGoodwill.com."""

    BASE_URL = "https://shopgoodwill.com"
    NAME = "shopgoodwill"

    # CSS selectors for ShopGoodwill's UI
    SELECTORS = {
        "listing": ".product-card, .item-card, [data-testid='product-card']",
        "title": ".product-title, .item-title, h3 a, .title",
        "price": ".product-price, .item-price, .price, .current-bid",
        "link": "a[href*='/item/'], a[href*='/product/']",
        "image": "img.product-image, img.item-image, .product-card img",
        "search_input": "input[type='search'], input[name='searchText'], #searchText",
        "search_button": "button[type='submit'], .search-button, [aria-label='Search']",
        "next_page": ".pagination .next, a[aria-label='Next'], .page-next",
        "no_results": ".no-results, .empty-results",
    }

    async def search(self, page: Page, queries: list[str]) -> AsyncIterator[Listing]:
        """Search ShopGoodwill and yield listings.

        Args:
            page: Playwright page instance.
            queries: List of search query strings.

        Yields:
            Listing objects for each result found.
        """
        for query in queries:
            logger.info(f"Searching ShopGoodwill for: {query}")

            try:
                # Navigate to search results
                search_url = f"{self.BASE_URL}/search?q={quote_plus(query)}&category=Jewelry"
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
                logger.warning(f"Timeout searching ShopGoodwill for: {query}")
            except Exception as e:
                logger.error(f"Error searching ShopGoodwill: {e}")

    async def _extract_listings(self, page: Page) -> AsyncIterator[Listing]:
        """Extract listings from current page.

        Args:
            page: Playwright page instance.

        Yields:
            Listing objects for each item on the page.
        """
        # Wait for listings to load
        try:
            await page.wait_for_selector(
                self.SELECTORS["listing"],
                timeout=10000,
            )
        except PlaywrightTimeout:
            logger.warning("No listings found on page")
            return

        # Get all listing elements
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

                url = urljoin(self.BASE_URL, href)

                # Extract title
                title_element = await element.query_selector(self.SELECTORS["title"])
                title = ""
                if title_element:
                    title = await title_element.text_content() or ""
                    title = title.strip()

                if not title:
                    # Fallback: try to get title from link text
                    title = await link_element.text_content() or ""
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
                    description=None,  # Description requires visiting detail page
                    image_url=image_url,
                )

            except Exception as e:
                logger.warning(f"Error extracting listing: {e}")

    async def _has_next_page(self, page: Page) -> bool:
        """Check if there's a next page of results.

        Args:
            page: Playwright page instance.

        Returns:
            True if next page exists and is clickable.
        """
        next_button = await page.query_selector(self.SELECTORS["next_page"])
        if not next_button:
            return False

        # Check if button is disabled
        is_disabled = await next_button.get_attribute("disabled")
        if is_disabled:
            return False

        # Check for disabled class
        class_attr = await next_button.get_attribute("class") or ""
        if "disabled" in class_attr.lower():
            return False

        return True

    async def _go_to_next_page(self, page: Page) -> None:
        """Navigate to the next page of results.

        Args:
            page: Playwright page instance.
        """
        next_button = await page.query_selector(self.SELECTORS["next_page"])
        if next_button:
            await next_button.click()
            await page.wait_for_load_state("domcontentloaded")

    async def get_listing_details(self, page: Page, url: str) -> Listing | None:
        """Get detailed information for a specific listing.

        Args:
            page: Playwright page instance.
            url: URL of the listing to fetch.

        Returns:
            Listing with full details, or None if fetch failed.
        """
        try:
            await page.goto(url, wait_until="domcontentloaded")
            await self._rate_limit()

            # Extract title
            title_element = await page.query_selector("h1, .product-title, .item-title")
            title = ""
            if title_element:
                title = await title_element.text_content() or ""
                title = title.strip()

            # Extract price
            price_element = await page.query_selector(".current-bid, .price, .product-price")
            price = None
            if price_element:
                price = await price_element.text_content()
                if price:
                    price = price.strip()

            # Extract description
            desc_element = await page.query_selector(".description, .product-description, .item-description")
            description = None
            if desc_element:
                description = await desc_element.text_content()
                if description:
                    description = description.strip()

            # Extract image
            image_element = await page.query_selector(".product-image img, .main-image img, .gallery img")
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
            logger.error(f"Error fetching listing details: {e}")
            return None
