"""Bridge to legacy marketplace adapters."""

import logging
import re
from typing import TYPE_CHECKING
from urllib.parse import urlparse

from playwright.async_api import Page

from src.extractors.base import ExtractedListing, ListingExtractor

if TYPE_CHECKING:
    from src.adapters.base import MarketplaceAdapter

logger = logging.getLogger(__name__)


# Domain to adapter name mapping
DOMAIN_ADAPTER_MAP = {
    r"ebay\.(com|co\.uk|de|fr|ca|au)": "ebay",
    r"etsy\.com": "etsy",
    r"shopgoodwill\.com": "shopgoodwill",
    r"poshmark\.com": "poshmark",
    r"mercari\.com": "mercari",
    r"rubylane\.com": "rubylane",
    r"craigslist\.org": "craigslist",
}


class LegacyAdapterBridge(ListingExtractor):
    """Bridge to use legacy marketplace adapters for extraction.

    When a URL matches a known marketplace domain, uses the corresponding
    legacy adapter's get_listing_details() method for extraction.
    """

    NAME = "legacy"

    def __init__(self, adapters: dict[str, "MarketplaceAdapter"] | None = None):
        """Initialize with adapter instances.

        Args:
            adapters: Dictionary mapping adapter names to instances.
                     If None, will lazy-load adapters when needed.
        """
        self._adapters = adapters or {}
        self._adapter_map = DOMAIN_ADAPTER_MAP

    def _detect_adapter(self, url: str) -> str | None:
        """Detect which adapter should handle a URL.

        Args:
            url: URL to analyze.

        Returns:
            Adapter name or None.
        """
        try:
            parsed = urlparse(url)
            domain = parsed.netloc.lower()

            for pattern, adapter_name in self._adapter_map.items():
                if re.search(pattern, domain, re.IGNORECASE):
                    return adapter_name

            return None
        except Exception:
            return None

    def _get_adapter(self, name: str) -> "MarketplaceAdapter | None":
        """Get or create an adapter instance.

        Args:
            name: Adapter name.

        Returns:
            Adapter instance or None.
        """
        if name in self._adapters:
            return self._adapters[name]

        # Lazy load adapters
        try:
            from src.adapters import ADAPTER_MAP

            if name in ADAPTER_MAP:
                adapter_class = ADAPTER_MAP[name]
                self._adapters[name] = adapter_class()
                return self._adapters[name]
        except ImportError as e:
            logger.warning(f"Could not import adapter {name}: {e}")

        return None

    async def can_extract(self, page: Page, url: str) -> bool:
        """Check if a legacy adapter can handle this URL.

        Args:
            page: Playwright page instance.
            url: The URL of the page.

        Returns:
            True if a legacy adapter is available.
        """
        adapter_name = self._detect_adapter(url)
        if adapter_name:
            adapter = self._get_adapter(adapter_name)
            return adapter is not None
        return False

    async def extract(self, page: Page, url: str) -> ExtractedListing | None:
        """Extract listing using legacy adapter.

        Args:
            page: Playwright page instance.
            url: The URL of the page.

        Returns:
            ExtractedListing or None.
        """
        adapter_name = self._detect_adapter(url)
        if not adapter_name:
            return None

        adapter = self._get_adapter(adapter_name)
        if not adapter:
            return None

        try:
            # Use the adapter's get_listing_details method
            listing = await adapter.get_listing_details(page, url)

            if listing:
                return ExtractedListing(
                    url=listing.url,
                    title=listing.title,
                    price=listing.price,
                    description=listing.description,
                    image_url=listing.image_url,
                    source=listing.source,
                    extraction_method="legacy",
                    confidence=0.8,  # High confidence for dedicated adapter
                )
        except Exception as e:
            logger.warning(f"Legacy adapter {adapter_name} failed: {e}")

        return None
