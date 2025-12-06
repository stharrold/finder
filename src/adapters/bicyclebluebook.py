"""BicycleBlueBook marketplace adapter for bike listings."""

import logging
from typing import AsyncIterator
from urllib.parse import quote_plus

from playwright.async_api import Page
from playwright.async_api import TimeoutError as PlaywrightTimeout

from src.adapters.base import MarketplaceAdapter
from src.models import Listing

logger = logging.getLogger(__name__)


class BicycleBlueBookAdapter(MarketplaceAdapter):
    """Adapter for searching BicycleBlueBook marketplace."""

    BASE_URL = "https://www.bicyclebluebook.com"
    NAME = "bicyclebluebook"

    SELECTORS = {
        "listing": ".listing-card, .product-card, [data-listing-id], .search-result-item",
        "title": ".listing-title, .product-title, h2, h3",
        "price": ".listing-price, .price, .sale-price",
        "link": "a[href*='/listing/']",
        "image": ".listing-image img, .product-image img, img",
        "location": ".listing-location, .location, .seller-location",
        "condition": ".condition, .listing-condition",
        "no_results": ".no-results, .empty-results, .no-listings",
        "next_page": ".pagination .next, a[rel='next'], .page-next",
        # Detail page selectors
        "detail_title": "h1",
        "detail_price": ".price, .listing-price, [data-price]",
        "detail_condition": ".condition, [data-condition]",
        "detail_specs": ".specs, .specifications, .bike-specs, table",
        "detail_description": ".description, .listing-description",
        "detail_location": ".location, .seller-location",
        "detail_image": ".gallery img, .main-image img, .listing-image img",
    }

    # E-bike category filter
    CATEGORY_EBIKE = "e-bike"

    async def search(self, page: Page, queries: list[str]) -> AsyncIterator[Listing]:
        """Search BicycleBlueBook marketplace and yield listings.

        Args:
            page: Playwright page instance.
            queries: List of search query strings.

        Yields:
            Listing objects for each result found.
        """
        for query in queries:
            logger.info(f"Searching BicycleBlueBook for: {query}")

            try:
                # Navigate to search page
                # BicycleBlueBook URL format: /marketplace/search?q=query&category=e-bike
                search_url = (
                    f"{self.BASE_URL}/marketplace/search"
                    f"?q={quote_plus(query)}"
                    f"&category={self.CATEGORY_EBIKE}"
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
                logger.warning(f"Timeout searching BicycleBlueBook for: {query}")
            except Exception as e:
                logger.error(f"Error searching BicycleBlueBook: {e}")

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
                    # Try getting href from parent element if it's a link
                    href = await element.get_attribute("href")
                    if not href:
                        continue
                else:
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

                # Extract location
                location_element = await element.query_selector(self.SELECTORS["location"])
                location = None
                if location_element:
                    location = await location_element.text_content()
                    if location:
                        location = location.strip()

                # Extract condition
                condition_element = await element.query_selector(self.SELECTORS["condition"])
                condition = None
                if condition_element:
                    condition = await condition_element.text_content()
                    if condition:
                        condition = condition.strip()

                # Build description from location and condition
                description_parts = []
                if condition:
                    description_parts.append(f"Condition: {condition}")
                if location:
                    description_parts.append(f"Location: {location}")
                description = " | ".join(description_parts) if description_parts else None

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
            title_element = await page.query_selector(self.SELECTORS["detail_title"])
            title = ""
            if title_element:
                title = await title_element.text_content() or ""
                title = title.strip()

            # Extract price
            price_element = await page.query_selector(self.SELECTORS["detail_price"])
            price = None
            if price_element:
                price = await price_element.text_content()
                if price:
                    price = price.strip()

            # Extract description
            desc_element = await page.query_selector(self.SELECTORS["detail_description"])
            description = None
            if desc_element:
                description = await desc_element.text_content()
                if description:
                    description = description.strip()[:1000]

            # Extract condition
            condition_element = await page.query_selector(self.SELECTORS["detail_condition"])
            condition = None
            if condition_element:
                condition = await condition_element.text_content()
                if condition:
                    condition = condition.strip()

            # Extract location
            location_element = await page.query_selector(self.SELECTORS["detail_location"])
            location = None
            if location_element:
                location = await location_element.text_content()
                if location:
                    location = location.strip()

            # Extract specs
            specs_element = await page.query_selector(self.SELECTORS["detail_specs"])
            specs = None
            if specs_element:
                specs = await specs_element.text_content()
                if specs:
                    specs = specs.strip()

            # Build full description
            description_parts = []
            if description:
                description_parts.append(description)
            if condition:
                description_parts.append(f"Condition: {condition}")
            if location:
                description_parts.append(f"Location: {location}")
            if specs:
                description_parts.append(f"Specs: {specs[:500]}")

            full_description = "\n".join(description_parts) if description_parts else None

            # Extract image
            image_element = await page.query_selector(self.SELECTORS["detail_image"])
            image_url = None
            if image_element:
                image_url = await image_element.get_attribute("src")

            return Listing(
                url=url,
                source=self.NAME,
                title=title,
                price=price,
                description=full_description,
                image_url=image_url,
            )

        except Exception as e:
            logger.error(f"Error fetching BicycleBlueBook listing details: {e}")
            return None
