"""Base class for search discovery providers."""

import asyncio
import logging
from abc import ABC, abstractmethod
from collections.abc import AsyncGenerator
from dataclasses import dataclass, field

from playwright.async_api import Page

logger = logging.getLogger(__name__)


@dataclass
class DiscoveryResult:
    """Result from a search discovery query."""

    url: str
    title: str
    snippet: str | None = None
    source: str = ""  # 'google', 'duckduckgo', etc.
    marketplace: str | None = None  # Detected marketplace domain


@dataclass
class DiscoveryConfig:
    """Configuration for search discovery."""

    enabled: bool = True
    providers: list[str] = field(default_factory=lambda: ["duckduckgo"])
    rate_limit_delay: float = 2.0
    max_results_per_query: int = 20
    site_filters: list[str] = field(default_factory=list)  # e.g., ["site:ebay.com"]


class SearchDiscovery(ABC):
    """Abstract base class for search engine discovery providers.

    Discovers marketplace listings by querying search engines with ring keywords
    and extracting URLs of potential marketplace listings.
    """

    NAME: str = ""

    def __init__(
        self,
        rate_limit_delay: float = 2.0,
        max_results: int = 20,
    ):
        """Initialize discovery provider.

        Args:
            rate_limit_delay: Delay between requests in seconds.
            max_results: Maximum results to return per query.
        """
        self.rate_limit_delay = rate_limit_delay
        self.max_results = max_results

    async def _rate_limit(self) -> None:
        """Apply rate limiting delay."""
        await asyncio.sleep(self.rate_limit_delay)

    @abstractmethod
    def search(self, page: Page, query: str, site_filter: str | None = None) -> AsyncGenerator[DiscoveryResult, None]:
        """Search for marketplace listings.

        Args:
            page: Playwright page instance.
            query: Search query string.
            site_filter: Optional site restriction (e.g., "site:ebay.com").

        Yields:
            DiscoveryResult objects for each search result.
        """
        ...

    async def discover(
        self,
        page: Page,
        queries: list[str],
        site_filters: list[str] | None = None,
    ) -> AsyncGenerator[DiscoveryResult, None]:
        """Discover marketplace listings across multiple queries.

        Args:
            page: Playwright page instance.
            queries: List of search queries.
            site_filters: Optional list of site restrictions.

        Yields:
            Deduplicated DiscoveryResult objects.
        """
        seen_urls: set[str] = set()
        # List of site filter strings or [None] for no filter
        filter_list: list[str | None] = list(site_filters) if site_filters else [None]

        for query in queries:
            for site_filter in filter_list:
                try:
                    async for result in self.search(page, query, site_filter):
                        # Deduplicate by URL
                        if result.url not in seen_urls:
                            seen_urls.add(result.url)
                            result.source = self.NAME
                            yield result
                except Exception as e:
                    logger.error(f"Error in {self.NAME} discovery: {e}")


class AggregatedDiscovery:
    """Aggregates results from multiple search discovery providers."""

    def __init__(self, providers: list[SearchDiscovery]):
        """Initialize with list of providers.

        Args:
            providers: List of SearchDiscovery instances.
        """
        self.providers = providers

    async def discover_all(
        self,
        page: Page,
        queries: list[str],
        site_filters: list[str] | None = None,
    ) -> AsyncGenerator[DiscoveryResult, None]:
        """Discover listings from all providers.

        Args:
            page: Playwright page instance.
            queries: List of search queries.
            site_filters: Optional list of site restrictions.

        Yields:
            Deduplicated DiscoveryResult objects from all providers.
        """
        seen_urls: set[str] = set()

        for provider in self.providers:
            try:
                async for result in provider.discover(page, queries, site_filters):
                    if result.url not in seen_urls:
                        seen_urls.add(result.url)
                        yield result
            except Exception as e:
                logger.error(f"Error with provider {provider.NAME}: {e}")
