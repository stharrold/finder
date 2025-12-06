"""Generic listing extractor using heuristics."""

import logging
import re

from playwright.async_api import Page

from src.extractors.base import ExtractedListing, ListingExtractor

logger = logging.getLogger(__name__)


class GenericListingExtractor(ListingExtractor):
    """Extracts listing data using heuristics.

    Used as a fallback when structured data is not available.
    Uses visual and content heuristics to identify:
    - Title (h1, largest heading)
    - Price (currency patterns)
    - Description (main content area)
    - Images (largest product images)
    """

    NAME = "generic"

    # Common price patterns
    PRICE_PATTERNS = [
        r"\$[\d,]+(?:\.\d{2})?",  # $123.45 or $1,234
        r"£[\d,]+(?:\.\d{2})?",  # £123.45
        r"€[\d,]+(?:\.\d{2})?",  # €123.45
        r"USD\s*[\d,]+(?:\.\d{2})?",  # USD 123.45
        r"[\d,]+(?:\.\d{2})?\s*(?:USD|EUR|GBP)",  # 123.45 USD
    ]

    async def can_extract(self, page: Page, url: str) -> bool:
        """Always returns True as this is the fallback extractor.

        Args:
            page: Playwright page instance.
            url: The URL of the page.

        Returns:
            Always True.
        """
        return True

    async def extract(self, page: Page, url: str) -> ExtractedListing | None:
        """Extract listing data using heuristics.

        Args:
            page: Playwright page instance.
            url: The URL of the page.

        Returns:
            ExtractedListing with extracted data, or None.
        """
        # Extract data in a single JavaScript call
        data = await page.evaluate(
            """
            () => {
                const result = {
                    title: '',
                    description: '',
                    priceText: '',
                    imageUrl: null,
                    allText: ''
                };

                // 1. Find title (h1, or largest heading, or page title)
                const h1 = document.querySelector('h1');
                if (h1) {
                    result.title = h1.textContent.trim();
                } else {
                    // Try other headings
                    for (const level of ['h2', 'h3']) {
                        const heading = document.querySelector(level);
                        if (heading) {
                            result.title = heading.textContent.trim();
                            break;
                        }
                    }
                }

                // Fall back to page title
                if (!result.title) {
                    result.title = document.title || '';
                }

                // 2. Find description (main content, article, or largest text block)
                const contentSelectors = [
                    '[itemprop="description"]',
                    '.description',
                    '.product-description',
                    '.item-description',
                    'article p',
                    'main p',
                    '.content p'
                ];

                for (const selector of contentSelectors) {
                    const el = document.querySelector(selector);
                    if (el && el.textContent.trim().length > 50) {
                        result.description = el.textContent.trim().substring(0, 500);
                        break;
                    }
                }

                // 3. Collect all visible text for price extraction
                result.allText = document.body.innerText || '';

                // 4. Find price elements
                const priceSelectors = [
                    '[itemprop="price"]',
                    '.price',
                    '.product-price',
                    '.item-price',
                    '.listing-price',
                    '[class*="price"]',
                    '[data-price]'
                ];

                for (const selector of priceSelectors) {
                    const el = document.querySelector(selector);
                    if (el) {
                        const text = el.textContent.trim();
                        if (text.match(/[$£€]|USD|EUR|GBP/)) {
                            result.priceText = text;
                            break;
                        }
                    }
                }

                // 5. Find main product image
                const imageSelectors = [
                    '[itemprop="image"]',
                    '.product-image img',
                    '.listing-image img',
                    '.item-image img',
                    '.gallery img',
                    'main img[src*="product"]',
                    'main img[src*="item"]',
                    'img[alt*="product"]'
                ];

                for (const selector of imageSelectors) {
                    const el = document.querySelector(selector);
                    if (el) {
                        result.imageUrl = el.src || el.getAttribute('data-src');
                        if (result.imageUrl) break;
                    }
                }

                // Fallback: find largest image
                if (!result.imageUrl) {
                    const images = Array.from(document.querySelectorAll('img'))
                        .filter(img => img.naturalWidth > 200 && img.naturalHeight > 200)
                        .sort((a, b) =>
                            (b.naturalWidth * b.naturalHeight) -
                            (a.naturalWidth * a.naturalHeight)
                        );
                    if (images.length > 0) {
                        result.imageUrl = images[0].src;
                    }
                }

                return result;
            }
            """
        )

        title = data.get("title", "").strip()
        description = data.get("description", "")
        image_url = data.get("imageUrl")

        # Extract price from price text or all text
        price = self._extract_price(data.get("priceText", ""))
        if not price:
            price = self._extract_price(data.get("allText", ""))

        if not title:
            logger.warning(f"Could not extract title from: {url}")
            return None

        return ExtractedListing(
            url=url,
            title=title,
            price=price,
            description=description[:500] if description else None,
            image_url=image_url,
            source="generic",
            confidence=0.5,  # Lower confidence for heuristic extraction
            raw_data=data,
        )

    def _extract_price(self, text: str) -> str | None:
        """Extract price from text using regex patterns.

        Args:
            text: Text to search for price.

        Returns:
            First matched price or None.
        """
        if not text:
            return None

        for pattern in self.PRICE_PATTERNS:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                return match.group(0).strip()

        return None
