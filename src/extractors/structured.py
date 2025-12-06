"""Structured data extractor for JSON-LD, OpenGraph, and microdata."""

import logging

from playwright.async_api import Page

from src.extractors.base import ExtractedListing, ListingExtractor

logger = logging.getLogger(__name__)

# ISO 4217 currency code to symbol mapping
CURRENCY_SYMBOLS: dict[str, str] = {
    "USD": "$",
    "EUR": "€",
    "GBP": "£",
    "CAD": "C$",
    "AUD": "A$",
}

# Maximum description length before truncation
MAX_DESCRIPTION_LENGTH = 500


class StructuredDataExtractor(ListingExtractor):
    """Extracts listing data from structured markup.

    Supports:
    - JSON-LD (Schema.org Product)
    - OpenGraph meta tags
    - Schema.org microdata
    """

    NAME = "structured"

    async def can_extract(self, page: Page, url: str) -> bool:
        """Check if page has structured data.

        Args:
            page: Playwright page instance.
            url: The URL of the page.

        Returns:
            True if structured data is present.
        """
        has_data = await page.evaluate(
            """
            () => {
                // Check for JSON-LD
                const jsonLd = document.querySelector(
                    'script[type="application/ld+json"]'
                );
                if (jsonLd) return true;

                // Check for OpenGraph
                const ogTitle = document.querySelector('meta[property="og:title"]');
                if (ogTitle) return true;

                // Check for microdata
                const itemscope = document.querySelector('[itemscope]');
                if (itemscope) return true;

                return false;
            }
            """
        )
        return bool(has_data)

    async def extract(self, page: Page, url: str) -> ExtractedListing | None:
        """Extract listing data from structured markup.

        Args:
            page: Playwright page instance.
            url: The URL of the page.

        Returns:
            ExtractedListing with extracted data, or None.
        """
        # Extract all structured data in one JS call
        data = await page.evaluate(
            """
            () => {
                const result = {
                    jsonLd: null,
                    openGraph: {},
                    microdata: {}
                };

                // Extract JSON-LD
                const jsonLdScripts = document.querySelectorAll(
                    'script[type="application/ld+json"]'
                );
                for (const script of jsonLdScripts) {
                    try {
                        const parsed = JSON.parse(script.textContent);
                        // Look for Product schema
                        if (parsed['@type'] === 'Product' ||
                            (Array.isArray(parsed['@graph']) &&
                             parsed['@graph'].some(item => item['@type'] === 'Product'))) {
                            result.jsonLd = parsed;
                            break;
                        }
                        // Also accept if it has offers (likely a product)
                        if (parsed.offers || parsed.price) {
                            result.jsonLd = parsed;
                            break;
                        }
                    } catch (e) {
                        // Invalid JSON, skip
                    }
                }

                // Extract OpenGraph
                const ogTags = document.querySelectorAll('meta[property^="og:"]');
                ogTags.forEach(tag => {
                    const property = tag.getAttribute('property').replace('og:', '');
                    result.openGraph[property] = tag.getAttribute('content');
                });

                // Also get product-specific meta
                const productTags = document.querySelectorAll(
                    'meta[property^="product:"]'
                );
                productTags.forEach(tag => {
                    const property = tag.getAttribute('property').replace('product:', '');
                    result.openGraph['product_' + property] = tag.getAttribute('content');
                });

                // Extract microdata
                const itemscope = document.querySelector(
                    '[itemscope][itemtype*="Product"], [itemscope][itemtype*="Offer"]'
                );
                if (itemscope) {
                    const props = itemscope.querySelectorAll('[itemprop]');
                    props.forEach(prop => {
                        const name = prop.getAttribute('itemprop');
                        result.microdata[name] = prop.getAttribute('content') ||
                                                  prop.textContent.trim();
                    });
                }

                return result;
            }
            """
        )

        # Try to extract from each source in order of preference
        listing = None

        # 1. JSON-LD (most reliable)
        if data.get("jsonLd"):
            listing = self._parse_json_ld(data["jsonLd"], url)

        # 2. OpenGraph (common on social-friendly sites)
        if not listing and data.get("openGraph"):
            listing = self._parse_open_graph(data["openGraph"], url)

        # 3. Microdata (less common but still useful)
        if not listing and data.get("microdata"):
            listing = self._parse_microdata(data["microdata"], url)

        if listing:
            listing.raw_data = data
            listing.source = "structured"

        return listing

    def _parse_json_ld(self, json_data: dict, url: str) -> ExtractedListing | None:
        """Parse JSON-LD Product schema.

        Args:
            json_data: Parsed JSON-LD data.
            url: Page URL.

        Returns:
            ExtractedListing or None.
        """
        try:
            # Handle @graph wrapper
            product = json_data
            if "@graph" in json_data:
                product = next(
                    (item for item in json_data["@graph"] if item.get("@type") == "Product"),
                    json_data,
                )

            title = product.get("name", "")
            description = product.get("description", "")

            # Extract price from offers
            price = None
            offers = product.get("offers", {})
            if isinstance(offers, list):
                offers = offers[0] if offers else {}
            if isinstance(offers, dict):
                price = offers.get("price")
                if price:
                    currency_code = offers.get("priceCurrency", "USD")
                    symbol = CURRENCY_SYMBOLS.get(currency_code, currency_code)
                    price = f"{symbol}{price}"

            # Direct price
            if not price and product.get("price"):
                price = str(product["price"])

            # Extract image
            image_url = product.get("image")
            if isinstance(image_url, list):
                image_url = image_url[0] if image_url else None
            if isinstance(image_url, dict):
                image_url = image_url.get("url")

            if title:
                return ExtractedListing(
                    url=url,
                    title=title,
                    price=price,
                    description=self._truncate(description) if description else None,
                    image_url=image_url,
                    confidence=0.9,  # High confidence for JSON-LD
                )
        except Exception as e:
            logger.warning(f"Error parsing JSON-LD: {e}")

        return None

    def _parse_open_graph(self, og_data: dict, url: str) -> ExtractedListing | None:
        """Parse OpenGraph meta tags.

        Args:
            og_data: Dictionary of OpenGraph properties.
            url: Page URL.

        Returns:
            ExtractedListing or None.
        """
        try:
            title = og_data.get("title", "")
            description = og_data.get("description", "")
            image_url = og_data.get("image")

            # Try to get price from product:price:amount
            price = og_data.get("product_price:amount")
            if price:
                currency_code = og_data.get("product_price:currency", "USD")
                symbol = CURRENCY_SYMBOLS.get(currency_code, currency_code)
                price = f"{symbol}{price}"

            if title:
                return ExtractedListing(
                    url=url,
                    title=title,
                    price=price,
                    description=self._truncate(description) if description else None,
                    image_url=image_url,
                    confidence=0.7,  # Medium confidence for OG
                )
        except Exception as e:
            logger.warning(f"Error parsing OpenGraph: {e}")

        return None

    def _parse_microdata(self, microdata: dict, url: str) -> ExtractedListing | None:
        """Parse Schema.org microdata.

        Args:
            microdata: Dictionary of microdata properties.
            url: Page URL.

        Returns:
            ExtractedListing or None.
        """
        try:
            title = microdata.get("name", "")
            description = microdata.get("description", "")
            price = microdata.get("price")
            image_url = microdata.get("image")

            if title:
                return ExtractedListing(
                    url=url,
                    title=title,
                    price=price,
                    description=self._truncate(description) if description else None,
                    image_url=image_url,
                    confidence=0.6,  # Lower confidence for microdata
                )
        except Exception as e:
            logger.warning(f"Error parsing microdata: {e}")

        return None

    def _truncate(self, text: str) -> str:
        """Truncate text with ellipsis if it exceeds max length.

        Args:
            text: Text to truncate.

        Returns:
            Truncated text with ellipsis if needed.
        """
        if len(text) <= MAX_DESCRIPTION_LENGTH:
            return text
        return text[: MAX_DESCRIPTION_LENGTH - 3] + "..."
