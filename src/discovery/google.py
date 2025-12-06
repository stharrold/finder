"""Google Search discovery provider."""

import logging
import re
from collections.abc import AsyncGenerator
from urllib.parse import quote_plus, unquote, urlparse

from playwright.async_api import Page
from playwright.async_api import TimeoutError as PlaywrightTimeout

from src.discovery.base import DiscoveryResult, SearchDiscovery

logger = logging.getLogger(__name__)


class GoogleDiscovery(SearchDiscovery):
    """Discover marketplace listings via Google Search.

    Uses browser-based search to avoid API costs and access real-time results.
    Implements rate limiting to respect Google's terms of service.

    WARNING: Automated scraping of Google Search results may violate Google's
    Terms of Service. For production or ToS-compliant use, consider using the
    official Google Custom Search JSON API instead:
    https://developers.google.com/custom-search/v1/overview
    """

    NAME = "google"
    BASE_URL = "https://www.google.com/search"

    def __init__(self, *args, **kwargs):
        """Initialize Google discovery with ToS warning."""
        super().__init__(*args, **kwargs)
        logger.warning(
            "Google Search scraping may violate ToS. For production use, "
            "consider the official Google Custom Search JSON API: "
            "https://developers.google.com/custom-search/v1/overview"
        )

    async def search(self, page: Page, query: str, site_filter: str | None = None) -> AsyncGenerator[DiscoveryResult, None]:
        """Search Google for marketplace listings.

        Args:
            page: Playwright page instance.
            query: Search query string.
            site_filter: Optional site restriction (e.g., "site:ebay.com").

        Yields:
            DiscoveryResult objects for each search result.
        """
        # Build search query with optional site filter
        full_query = f"{site_filter} {query}" if site_filter else query
        search_url = f"{self.BASE_URL}?q={quote_plus(full_query)}"

        logger.info(f"Google search: {full_query}")

        try:
            await page.goto(search_url, wait_until="domcontentloaded")
            await self._rate_limit()

            # Wait for search results
            await page.wait_for_selector("#search", timeout=10000)

            # Extract results using batch JavaScript
            results = await page.evaluate(
                """
                () => {
                    const results = [];
                    // Google search result selectors
                    const items = document.querySelectorAll('#search .g, #rso .g');

                    items.forEach(item => {
                        try {
                            // Find the link
                            const linkEl = item.querySelector('a[href^="http"]');
                            if (!linkEl) return;

                            const href = linkEl.getAttribute('href');
                            if (!href || href.includes('google.com')) return;

                            // Extract clean URL (handle Google redirect URLs)
                            let url = href;
                            if (href.includes('/url?')) {
                                const match = href.match(/[?&]q=([^&]+)/);
                                if (match) {
                                    url = decodeURIComponent(match[1]);
                                }
                            }

                            // Get title
                            const titleEl = item.querySelector('h3');
                            const title = titleEl ? titleEl.textContent.trim() : '';

                            // Get snippet
                            const snippetEl = item.querySelector(
                                '[data-sncf], .VwiC3b, .IsZvec'
                            );
                            const snippet = snippetEl
                                ? snippetEl.textContent.trim()
                                : '';

                            if (url && title) {
                                results.push({
                                    url: url,
                                    title: title,
                                    snippet: snippet
                                });
                            }
                        } catch (e) {
                            // Skip problematic elements
                        }
                    });

                    return results;
                }
                """
            )

            count = 0
            for result in results:
                if count >= self.max_results:
                    break

                url = result.get("url", "")
                # Clean up URL
                url = self._clean_url(url)
                if not url:
                    continue

                yield DiscoveryResult(
                    url=url,
                    title=result.get("title", ""),
                    snippet=result.get("snippet"),
                    source=self.NAME,
                    marketplace=self._detect_marketplace(url),
                )
                count += 1

        except PlaywrightTimeout:
            logger.warning(f"Timeout searching Google for: {query}")
        except Exception as e:
            logger.error(f"Error in Google search: {e}")

    def _clean_url(self, url: str) -> str:
        """Clean and validate URL.

        Args:
            url: Raw URL from search results.

        Returns:
            Cleaned URL or empty string if invalid.
        """
        try:
            # Decode URL-encoded characters
            url = unquote(url)

            # Parse and validate
            parsed = urlparse(url)
            if not parsed.scheme or not parsed.netloc:
                return ""

            # Skip Google internal URLs
            if "google.com" in parsed.netloc:
                return ""

            return url
        except Exception:
            return ""

    def _detect_marketplace(self, url: str) -> str | None:
        """Detect marketplace from URL.

        Args:
            url: URL to analyze.

        Returns:
            Marketplace name or None.
        """
        domain_patterns = {
            "ebay": r"ebay\.(com|co\.uk|de|fr)",
            "etsy": r"etsy\.com",
            "shopgoodwill": r"shopgoodwill\.com",
            "poshmark": r"poshmark\.com",
            "mercari": r"mercari\.com",
            "rubylane": r"rubylane\.com",
            "craigslist": r"craigslist\.org",
            "facebook": r"facebook\.com/marketplace",
            "offerup": r"offerup\.com",
            "depop": r"depop\.com",
        }

        for marketplace, pattern in domain_patterns.items():
            if re.search(pattern, url, re.IGNORECASE):
                return marketplace

        return None
