"""Trek Red Barn Refresh (certified pre-owned) marketplace adapter."""

import logging
from typing import AsyncIterator
from urllib.parse import quote_plus

from playwright.async_api import Page
from playwright.async_api import TimeoutError as PlaywrightTimeout

from src.adapters.base import MarketplaceAdapter
from src.models import Listing

logger = logging.getLogger(__name__)


class TrekRedBarnAdapter(MarketplaceAdapter):
    """Adapter for searching Trek Red Barn Refresh certified pre-owned bikes."""

    BASE_URL = "https://www.trekbikes.com"
    NAME = "trek_redbarn"

    # Red Barn Refresh / Certified Pre-Owned section
    CPO_PATH = "/us/en_US/certified-preowned"

    SELECTORS = {
        "listing": ".product-tile, .product-card, [data-component='product-tile']",
        "title": ".product-tile__title, .product-name, h3 a",
        "price": ".product-tile__price, .price, .sale-price",
        "link": ".product-tile__link, a.product-link, h3 a",
        "image": ".product-tile__image img, .product-image img",
        "category": ".product-tile__category, .category-badge",
        "no_results": ".no-results, .empty-search",
        "next_page": ".pagination .next, a[aria-label='Next page']",
        # Detail page selectors
        "specs": ".product-specs, .specifications, [data-component='specifications']",
        "description": ".product-description, .description",
    }

    async def search(self, page: Page, queries: list[str]) -> AsyncIterator[Listing]:
        """Search Trek Red Barn Refresh and yield listings.

        Args:
            page: Playwright page instance.
            queries: List of search query strings.

        Yields:
            Listing objects for each result found.
        """
        for query in queries:
            logger.info(f"Searching Trek Red Barn for: {query}")

            try:
                # Navigate to certified pre-owned search
                # Trek site search format: /us/en_US/search/?q=query&cgid=cpo-bikes
                search_url = (
                    f"{self.BASE_URL}/us/en_US/search/"
                    f"?q={quote_plus(query)}"
                    f"&cgid=cpo-bikes"  # Certified Pre-Owned category
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
                logger.warning(f"Timeout searching Trek Red Barn for: {query}")
            except Exception as e:
                logger.error(f"Error searching Trek Red Barn: {e}")

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
                    # Handle lazy loading - check for placeholder indicators
                    # Common patterns: placeholder URLs, data URIs, or missing src
                    if image_url:
                        is_placeholder = (
                            "placeholder" in image_url.lower()
                            or "data:image" in image_url  # Base64 placeholder
                            or "blank.gif" in image_url.lower()
                            or "spacer" in image_url.lower()
                            or image_url.startswith("data:")
                            or len(image_url) < 10  # Too short to be real URL
                        )
                        if is_placeholder:
                            image_url = await image_element.get_attribute("data-src")
                    else:
                        # No src attribute, try data-src for lazy loading
                        image_url = await image_element.get_attribute("data-src")

                # Extract category badge (e.g., "E-Bike")
                category_element = await element.query_selector(self.SELECTORS["category"])
                description = None
                if category_element:
                    category = await category_element.text_content()
                    if category:
                        description = f"Category: {category.strip()}"

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
        """Get detailed information for a specific listing.

        Extracts bike specifications including battery, class, and frame size.
        """
        try:
            await page.goto(url, wait_until="domcontentloaded")
            await self._rate_limit()

            # Extract title
            title_element = await page.query_selector("h1.product-name, h1")
            title = ""
            if title_element:
                title = await title_element.text_content() or ""
                title = title.strip()

            # Extract price
            price_element = await page.query_selector(".product-price, .price, [data-component='price']")
            price = None
            if price_element:
                price = await price_element.text_content()
                if price:
                    price = price.strip()

            # Extract description
            desc_element = await page.query_selector(self.SELECTORS["description"])
            description = None
            if desc_element:
                description = await desc_element.text_content()
                if description:
                    description = description.strip()[:500]

            # Extract specifications (critical for bike matching)
            specs_text = await self._extract_specifications(page)
            if specs_text:
                if description:
                    description = f"{description}\n\nSpecifications:\n{specs_text}"
                else:
                    description = f"Specifications:\n{specs_text}"

            # Extract image
            image_element = await page.query_selector(
                ".product-image img, .gallery-image img, [data-component='gallery'] img"
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
            logger.error(f"Error fetching Trek Red Barn listing details: {e}")
            return None

    async def _extract_specifications(self, page: Page) -> str | None:
        """Extract bike specifications from product page.

        Looks for key e-bike specs: battery, motor, class, frame size.
        """
        try:
            specs_element = await page.query_selector(self.SELECTORS["specs"])
            if not specs_element:
                return None

            # Get all spec rows
            spec_rows = await specs_element.query_selector_all(".spec-row, tr, .specification-item")

            specs = []
            key_specs = ["battery", "motor", "class", "frame", "size", "range"]

            for row in spec_rows:
                text = await row.text_content()
                if text:
                    text = text.strip().lower()
                    # Include if it contains key bike specs
                    if any(key in text for key in key_specs):
                        specs.append(text)

            return "\n".join(specs) if specs else None

        except Exception as e:
            logger.warning(f"Error extracting specifications: {e}")
            return None
