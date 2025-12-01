"""Base marketplace adapter interface."""

import asyncio
import random
from abc import ABC, abstractmethod
from typing import AsyncIterator

from playwright.async_api import Page

from src.models import Listing


class MarketplaceAdapter(ABC):
    """Abstract base class for marketplace-specific scrapers."""

    # Override these in subclasses
    BASE_URL: str = ""
    NAME: str = ""
    SELECTORS: dict[str, str] = {}

    def __init__(
        self,
        min_delay: float = 2.0,
        max_delay: float = 5.0,
    ):
        """Initialize adapter with rate limiting settings.

        Args:
            min_delay: Minimum delay between requests in seconds.
            max_delay: Maximum delay between requests in seconds.
        """
        self.min_delay = min_delay
        self.max_delay = max_delay

    async def _rate_limit(self) -> None:
        """Apply rate limiting delay between requests."""
        delay = random.uniform(self.min_delay, self.max_delay)
        await asyncio.sleep(delay)

    @abstractmethod
    def search(self, page: Page, queries: list[str]) -> AsyncIterator[Listing]:
        """Search marketplace and yield listings.

        Args:
            page: Playwright page instance.
            queries: List of search query strings.

        Yields:
            Listing objects for each result found.
        """
        ...

    @abstractmethod
    async def get_listing_details(self, page: Page, url: str) -> Listing | None:
        """Get detailed information for a specific listing.

        Args:
            page: Playwright page instance.
            url: URL of the listing to fetch.

        Returns:
            Listing with full details, or None if fetch failed.
        """
        pass

    def _extract_text(self, element: str | None, default: str = "") -> str:
        """Safely extract text from element.

        Args:
            element: Text content or None.
            default: Default value if element is None.

        Returns:
            Text content or default value.
        """
        if element is None:
            return default
        return element.strip()
