"""Craigslist marketplace adapter with multi-region support."""

import logging
from typing import AsyncIterator
from urllib.parse import quote_plus

from playwright.async_api import Page
from playwright.async_api import TimeoutError as PlaywrightTimeout

from src.adapters.base import MarketplaceAdapter
from src.models import Listing

logger = logging.getLogger(__name__)


class CraigslistAdapter(MarketplaceAdapter):
    """Adapter for searching Craigslist with multi-region support."""

    BASE_URL = "https://{region}.craigslist.org"
    NAME = "craigslist"

    # Region codes for Indianapolis area
    DEFAULT_REGIONS = [
        "indianapolis",
        "bloomington",
        "fortwayne",
        "louisville",
        "cincinnati",
    ]

    SELECTORS = {
        "listing": ".result-row, .cl-search-result, [data-pid]",
        "title": ".result-title, .posting-title, a.cl-app-anchor",
        "price": ".result-price, .priceinfo",
        "link": "a.result-title, a.posting-title, a.cl-app-anchor",
        "image": ".result-image img, .swipe img",
        "next_page": ".next, [aria-label='next page']",
        "no_results": ".noresults, .no-results",
    }

    def __init__(
        self,
        regions: list[str] | None = None,
        min_delay: float = 2.0,
        max_delay: float = 5.0,
    ):
        """Initialize adapter with region configuration.

        Args:
            regions: List of Craigslist region codes to search.
            min_delay: Minimum delay between requests in seconds.
            max_delay: Maximum delay between requests in seconds.
        """
        super().__init__(min_delay=min_delay, max_delay=max_delay)
        self.regions = regions or self.DEFAULT_REGIONS

    def _get_region_url(self, region: str) -> str:
        """Get base URL for a specific region."""
        return self.BASE_URL.format(region=region)

    async def search(self, page: Page, queries: list[str]) -> AsyncIterator[Listing]:
        """Search Craigslist across configured regions.

        Args:
            page: Playwright page instance.
            queries: List of search query strings.

        Yields:
            Listing objects for each result found.
        """
        for region in self.regions:
            base_url = self._get_region_url(region)

            for query in queries:
                logger.info(f"Searching Craigslist {region} for: {query}")

                try:
                    # Navigate to search results - jewelry category
                    search_url = (
                        f"{base_url}/search/jwa"  # Jewelry category
                        f"?query={quote_plus(query)}"
                    )
                    await page.goto(search_url, wait_until="domcontentloaded")
                    await self._rate_limit()

                    # Check for no results
                    no_results = await page.query_selector(self.SELECTORS["no_results"])
                    if no_results:
                        logger.info(f"No results in {region} for: {query}")
                        continue

                    # Process current page
                    async for listing in self._extract_listings(page, region):
                        yield listing

                    # Handle pagination (up to 2 pages per region/query)
                    for page_num in range(2, 3):
                        if not await self._has_next_page(page):
                            break

                        await self._go_to_next_page(page)
                        await self._rate_limit()

                        async for listing in self._extract_listings(page, region):
                            yield listing

                except PlaywrightTimeout:
                    logger.warning(f"Timeout searching Craigslist {region} for: {query}")
                except Exception as e:
                    logger.error(f"Error searching Craigslist {region}: {e}")

    async def _extract_listings(self, page: Page, region: str) -> AsyncIterator[Listing]:
        """Extract listings from current page.

        Args:
            page: Playwright page instance.
            region: Current region being searched.

        Yields:
            Listing objects for each item on the page.
        """
        try:
            await page.wait_for_selector(self.SELECTORS["listing"], timeout=10000)
        except PlaywrightTimeout:
            logger.warning(f"No listings found in {region}")
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

                url = href
                if not url.startswith("http"):
                    url = f"{self._get_region_url(region)}{href}"

                # Extract title
                title = ""
                if link_element:
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
                    source=f"{self.NAME}_{region}",
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

        # Check if button has disabled class
        class_attr = await next_button.get_attribute("class") or ""
        return "disabled" not in class_attr.lower()

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

            # Determine region from URL
            region = "unknown"
            for r in self.regions:
                if r in url:
                    region = r
                    break

            # Extract title
            title_element = await page.query_selector("#titletextonly, .postingtitletext")
            title = ""
            if title_element:
                title = await title_element.text_content() or ""
                title = title.strip()

            # Extract price
            price_element = await page.query_selector(".price, .postinginfo")
            price = None
            if price_element:
                price = await price_element.text_content()
                if price:
                    price = price.strip()

            # Extract description
            desc_element = await page.query_selector("#postingbody")
            description = None
            if desc_element:
                description = await desc_element.text_content()
                if description:
                    description = description.strip()[:500]

            # Extract image
            image_element = await page.query_selector(".gallery img, .swipe img")
            image_url = None
            if image_element:
                image_url = await image_element.get_attribute("src")

            return Listing(
                url=url,
                source=f"{self.NAME}_{region}",
                title=title,
                price=price,
                description=description,
                image_url=image_url,
            )

        except Exception as e:
            logger.error(f"Error fetching Craigslist listing details: {e}")
            return None
