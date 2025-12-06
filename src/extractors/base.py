"""Base class for adaptive listing extractors."""

import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field

from playwright.async_api import Page

from src.models import Listing

logger = logging.getLogger(__name__)


@dataclass
class ExtractedListing:
    """Listing data extracted from a page."""

    url: str
    title: str
    price: str | None = None
    description: str | None = None
    image_url: str | None = None
    source: str = ""  # Marketplace or extractor name
    extraction_method: str = ""  # 'structured', 'generic', 'legacy'
    confidence: float = 1.0  # 0.0 - 1.0
    raw_data: dict = field(default_factory=dict)

    def to_listing(self) -> Listing:
        """Convert to standard Listing model.

        Returns:
            Listing object compatible with existing scoring.
        """
        return Listing(
            url=self.url,
            source=self.source,
            title=self.title,
            price=self.price,
            description=self.description,
            image_url=self.image_url,
        )


class ListingExtractor(ABC):
    """Abstract base class for listing extractors."""

    NAME: str = ""

    @abstractmethod
    async def extract(self, page: Page, url: str) -> ExtractedListing | None:
        """Extract listing data from a page.

        Args:
            page: Playwright page instance (already navigated to URL).
            url: The URL of the page.

        Returns:
            ExtractedListing with data, or None if extraction failed.
        """
        ...

    @abstractmethod
    async def can_extract(self, page: Page, url: str) -> bool:
        """Check if this extractor can handle the page.

        Args:
            page: Playwright page instance.
            url: The URL of the page.

        Returns:
            True if this extractor can extract data from the page.
        """
        ...


class AdaptiveExtractor:
    """Chains multiple extractors to handle any marketplace page.

    Tries extractors in order of preference:
    1. StructuredDataExtractor (JSON-LD, OpenGraph, microdata)
    2. LegacyAdapterBridge (known marketplace adapters)
    3. GenericListingExtractor (heuristic fallback)
    """

    def __init__(self, extractors: list[ListingExtractor] | None = None):
        """Initialize with list of extractors.

        Args:
            extractors: List of extractors in priority order.
                       If None, uses default chain.
        """
        self.extractors = extractors or []

    async def extract(self, page: Page, url: str) -> ExtractedListing | None:
        """Extract listing data using the best available extractor.

        Args:
            page: Playwright page instance (already navigated to URL).
            url: The URL of the page.

        Returns:
            ExtractedListing from first successful extractor, or None.
        """
        for extractor in self.extractors:
            try:
                if await extractor.can_extract(page, url):
                    result = await extractor.extract(page, url)
                    if result and result.title:  # Valid extraction
                        result.extraction_method = extractor.NAME
                        logger.info(f"Extracted listing from {url} using {extractor.NAME}")
                        return result
            except Exception as e:
                logger.warning(f"Extractor {extractor.NAME} failed: {e}")

        logger.warning(f"No extractor could handle: {url}")
        return None
